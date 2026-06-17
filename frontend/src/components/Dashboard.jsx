import React, { useState, useEffect } from 'react';

// Simple count-up animation hook
function useAnimatedCount(targetValue, duration = 1000) {
  const [count, setCount] = useState(0);

  useEffect(() => {
    let startTimestamp = null;
    const end = parseInt(targetValue, 10) || 0;
    
    if (end === 0) {
      setCount(0);
      return;
    }

    const step = (timestamp) => {
      if (!startTimestamp) startTimestamp = timestamp;
      const progress = Math.min((timestamp - startTimestamp) / duration, 1);
      setCount(Math.floor(progress * end));
      if (progress < 1) {
        window.requestAnimationFrame(step);
      } else {
        setCount(end);
      }
    };

    window.requestAnimationFrame(step);
  }, [targetValue, duration]);

  return count;
}

export default function Dashboard({ batch, backendUrl }) {
  const [currentBatch, setCurrentBatch] = useState(batch);
  const [activeTab, setActiveTab] = useState('all'); // all, valid, invalid
  const [transactions, setTransactions] = useState([]);
  const [headers, setHeaders] = useState([]);
  const [errorsList, setErrorsList] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalItems, setTotalItems] = useState(0);
  const perPage = 10;

  // Sync batch prop if it changes externally
  useEffect(() => {
    setCurrentBatch(batch);
  }, [batch]);

  // Poll batch status if it is not COMPLETED or FAILED
  useEffect(() => {
    if (currentBatch.status === 'COMPLETED' || currentBatch.status === 'FAILED') {
      return;
    }

    const interval = setInterval(async () => {
      try {
        const res = await fetch(`${backendUrl}/api/batches/${currentBatch.id}`);
        if (res.ok) {
          const data = await res.json();
          setCurrentBatch(data);
          if (data.status === 'COMPLETED' || data.status === 'FAILED') {
            clearInterval(interval);
          }
        }
      } catch (err) {
        console.error("Error polling batch in Dashboard:", err);
      }
    }, 1500);

    return () => clearInterval(interval);
  }, [currentBatch.id, currentBatch.status, backendUrl]);

  // Animating final summary totals
  const animatedTotal = useAnimatedCount(currentBatch.total_rows);
  const animatedValid = useAnimatedCount(currentBatch.valid_rows);
  const animatedError = useAnimatedCount(currentBatch.error_rows);

  // Load errors to render category counts
  useEffect(() => {
    const fetchErrors = async () => {
      try {
        const res = await fetch(`${backendUrl}/api/batches/${currentBatch.id}/errors`);
        if (res.ok) {
          const data = await res.json();
          setErrorsList(data);
        }
      } catch (err) {
        console.error("Error fetching errors:", err);
      }
    };
    fetchErrors();
  }, [currentBatch.id, currentBatch.status, backendUrl]);

  // Load paginated transactions based on active filters
  useEffect(() => {
    const fetchTransactions = async () => {
      try {
        let url = `${backendUrl}/api/batches/${currentBatch.id}/transactions?page=${currentPage}&per_page=${perPage}`;
        if (activeTab === 'valid') {
          url += '&is_valid=true';
        } else if (activeTab === 'invalid') {
          url += '&is_valid=false';
        }
        
        const res = await fetch(url);
        if (res.ok) {
          const data = await res.json();
          setTransactions(data.transactions);
          setHeaders(data.headers || []);
          setTotalPages(data.pages);
          setTotalItems(data.total_items);
        }
      } catch (err) {
        console.error("Error fetching transaction details:", err);
      }
    };
    fetchTransactions();
  }, [currentBatch.id, currentBatch.status, backendUrl, activeTab, currentPage]);

  // Group errors to show counts in bar chart
  const errorBreakdown = errorsList.reduce((acc, curr) => {
    const code = curr.error_code || 'OTHER_ERROR';
    acc[code] = (acc[code] || 0) + 1;
    return acc;
  }, {});

  const totalErrorsCount = errorsList.length || 1;
  const sortedErrors = Object.entries(errorBreakdown).sort((a, b) => b[1] - a[1]);

  // SVG Donut Calculations
  const radius = 50;
  const circumference = 2 * Math.PI * radius; // ~314.16
  const validPercent = currentBatch.total_rows > 0 ? (currentBatch.valid_rows / currentBatch.total_rows) * 100 : 0;
  const errorPercent = currentBatch.total_rows > 0 ? (currentBatch.error_rows / currentBatch.total_rows) * 100 : 0;
  
  const validStrokeOffset = circumference - (validPercent / 100) * circumference;
  const errorStrokeOffset = circumference - (errorPercent / 100) * circumference;

  // Filter local transactions on search query (for immediate page filtering)
  const filteredTransactions = transactions.filter(t => {
    const term = searchTerm.toLowerCase();
    if (!term) return true;
    const rowData = t.raw_data || {};
    return Object.values(rowData).some(val => 
      val !== null && val !== undefined && String(val).toLowerCase().includes(term)
    );
  });

  const getCellClassName = (tx, fieldName) => {
    // If transaction is invalid, check if this specific cell has errors
    if (tx.is_valid) return '';
    const hasCellErr = errorsList.some(e => e.row_number === tx.row_number && e.field_name.toLowerCase() === fieldName.toLowerCase());
    return hasCellErr ? 'cell-invalid' : '';
  };

  const getRowErrorTooltip = (tx, fieldName) => {
    const err = errorsList.find(e => e.row_number === tx.row_number && e.field_name.toLowerCase() === fieldName.toLowerCase());
    return err ? err.error_message : null;
  };

  return (
    <section className="dashboard-container">
      {/* Metrics Row */}
      <div className="metrics-grid">
        <article className="metric-card total">
          <div className="metric-label">Total Processed Rows</div>
          <div className="metric-val data-mono">{animatedTotal}</div>
          <div className="metric-desc">Spreadsheet records parsed</div>
        </article>
        
        <article className="metric-card valid">
          <div className="metric-label">Clean / Valid Rows</div>
          <div className="metric-val data-mono" style={{ color: 'var(--teal-valid)' }}>{animatedValid}</div>
          <div className="metric-desc">Passed all rule checks</div>
        </article>

        <article className="metric-card invalid">
          <div className="metric-label">Flagged / Error Rows</div>
          <div className="metric-val data-mono" style={{ color: 'var(--amber-flag)' }}>{animatedError}</div>
          <div className="metric-desc">Requires human inspection</div>
        </article>
      </div>

      {/* Visual Charts Row */}
      <div className="insights-grid">
        <article className="insights-card">
          <h3 style={{ marginBottom: '1rem' }}>Validation Composition</h3>
          <div className="chart-wrapper">
            <div className="chart-svg-container">
              <svg width="160" height="160" viewBox="0 0 120 120" style={{ transform: 'rotate(-90deg)' }}>
                {/* Background Ring */}
                <circle cx="60" cy="60" r={radius} fill="transparent" stroke="var(--gray-100)" strokeWidth="12" />
                
                {/* Valid Arc */}
                <circle 
                  cx="60" 
                  cy="60" 
                  r={radius} 
                  fill="transparent" 
                  stroke="var(--teal-valid)" 
                  strokeWidth="12" 
                  strokeDasharray={circumference}
                  strokeDashoffset={validStrokeOffset}
                  strokeLinecap="round"
                />

                {/* Error Arc (offset by valid arc percent to stack it) */}
                {currentBatch.error_rows > 0 && (
                  <circle 
                    cx="60" 
                    cy="60" 
                    r={radius} 
                    fill="transparent" 
                    stroke="var(--amber-flag)" 
                    strokeWidth="12" 
                    strokeDasharray={circumference}
                    strokeDashoffset={errorStrokeOffset}
                    style={{ transform: `rotate(${(validPercent / 100) * 360}deg)`, transformOrigin: '60px 60px' }}
                    strokeLinecap="round"
                  />
                )}
              </svg>
              <div className="chart-label-center">
                <div className="chart-label-number">
                  {currentBatch.total_rows > 0 ? Math.round((currentBatch.valid_rows / currentBatch.total_rows) * 100) : 0}%
                </div>
                <div className="chart-label-text">Clean Rate</div>
              </div>
            </div>

            <div className="chart-legend">
              <div className="legend-item">
                <div className="legend-color valid"></div>
                <span>Clean ({Math.round(validPercent)}%)</span>
              </div>
              <div className="legend-item">
                <div className="legend-color flagged"></div>
                <span>Flagged ({Math.round(errorPercent)}%)</span>
              </div>
            </div>
          </div>
        </article>

        <article className="insights-card">
          <h3>Error Distribution</h3>
          {errorsList.length === 0 ? (
            <div className="empty-state" style={{ padding: '2rem' }}>
              <div style={{ fontSize: '2rem' }}>🌿</div>
              <p style={{ fontSize: '0.9rem' }}>No errors flagged in this batch!</p>
            </div>
          ) : (
            <div className="errors-breakdown-list">
              {sortedErrors.slice(0, 4).map(([code, count]) => {
                const widthPercent = (count / totalErrorsCount) * 100;
                return (
                  <div key={code} className="error-bar-item">
                    <div className="error-bar-info">
                      <span className="error-bar-label data-mono" style={{ fontSize: '0.8rem' }}>{code}</span>
                      <span className="error-bar-count data-mono">{count}</span>
                    </div>
                    <div className="error-bar-track">
                      <div className="error-bar-fill" style={{ width: `${widthPercent}%` }}></div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </article>
      </div>

      {/* Downloader Section */}
      <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', alignItems: 'center' }}>
        {currentBatch.status !== 'COMPLETED' ? (
          <div className="empty-state" style={{ width: '100%', padding: '1.5rem', marginBottom: 0, flexDirection: 'row', gap: '1rem', justifyContent: 'center', background: 'rgba(245, 158, 11, 0.05)', border: '1px dashed var(--amber-flag)' }}>
            <div style={{ fontSize: '1.5rem', animation: 'spin 2s linear infinite' }}>⚙️</div>
            <div style={{ textAlign: 'left' }}>
              <h4 style={{ margin: 0, color: 'var(--ink-navy)' }}>Audit Validation In Progress</h4>
              <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--gray-500)' }}>
                We are currently processing and auditing your transaction dataset. Report links and downloads will activate automatically once finished.
              </p>
            </div>
          </div>
        ) : (
          <>
            <a 
              href={`${backendUrl}/api/batches/${currentBatch.id}/download/clean`}
              className="btn btn-success"
              style={{ flex: 1, justifyContent: 'center', minWidth: '220px', padding: '1rem' }}
            >
              ✓ Download Cleaned Transactions File
              {currentBatch.valid_rows > 50000 && <span style={{ fontSize: '0.75rem', fontWeight: 'normal', display: 'block' }}>(Split ZIP download)</span>}
            </a>
            {currentBatch.error_rows > 0 && (
              <a 
                href={`${backendUrl}/api/batches/${currentBatch.id}/download/errors`}
                className="btn btn-warning"
                style={{ flex: 1, justifyContent: 'center', minWidth: '220px', padding: '1rem' }}
              >
                ⚠️ Download Audit Error Report
              </a>
            )}
          </>
        )}
      </div>

      {/* Interactive Data Review Table */}
      <div className="table-card">
        <div className="table-actions-bar">
          <div className="tabs-header" style={{ marginBottom: 0, borderBottom: 'none' }}>
            <button 
              onClick={() => { setActiveTab('all'); setCurrentPage(1); }}
              className={`tab-btn ${activeTab === 'all' ? 'active' : ''}`}
            >
              All Records ({currentBatch.total_rows})
            </button>
            <button 
              onClick={() => { setActiveTab('valid'); setCurrentPage(1); }}
              className={`tab-btn ${activeTab === 'valid' ? 'active' : ''}`}
            >
              Valid Clean ({currentBatch.valid_rows})
            </button>
            <button 
              onClick={() => { setActiveTab('invalid'); setCurrentPage(1); }}
              className={`tab-btn ${activeTab === 'invalid' ? 'active' : ''}`}
            >
              Flags ({currentBatch.error_rows})
            </button>
          </div>

          <input 
            type="text" 
            placeholder="Filter current page..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="search-input"
          />
        </div>

        <div className="table-responsive">
          <table>
            <thead>
              <tr>
                <th style={{ width: '60px' }}>Row</th>
                {headers.map(h => (
                  <th key={h}>{h.replace(/_/g, ' ').toUpperCase()}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filteredTransactions.length === 0 ? (
                <tr>
                  <td colSpan={headers.length + 1} className="empty-state">
                    <div className="empty-state-icon">🔍</div>
                    <p>No matching transactions found on this page.</p>
                  </td>
                </tr>
              ) : (
                filteredTransactions.map(tx => {
                  const rowData = tx.raw_data || {};
                  return (
                    <tr key={tx.id} className={tx.is_valid ? '' : 'tr-flagged'}>
                      <td className="data-mono" style={{ color: 'var(--gray-400)' }}>#{tx.row_number}</td>
                      {headers.map(h => {
                        const cellVal = rowData[h];
                        const isInvalid = getCellClassName(tx, h);
                        return (
                          <td 
                            key={h} 
                            className={isInvalid ? 'cell-invalid' : ''} 
                            title={getRowErrorTooltip(tx, h)}
                          >
                            {cellVal !== null && cellVal !== undefined ? String(cellVal) : ''}
                          </td>
                        );
                      })}
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination bar */}
        {totalPages > 1 && (
          <div className="pagination">
            <span className="pagination-info">
              Showing page <span className="data-mono" style={{ fontWeight: '600' }}>{currentPage}</span> of <span className="data-mono" style={{ fontWeight: '600' }}>{totalPages}</span> ({totalItems} records)
            </span>
            <div className="pagination-buttons">
              <button 
                onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
                disabled={currentPage === 1}
                className="btn btn-secondary"
                style={{ padding: '0.4rem 0.8rem', fontSize: '0.8rem' }}
              >
                Previous
              </button>
              <button 
                onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
                disabled={currentPage === totalPages}
                className="btn btn-secondary"
                style={{ padding: '0.4rem 0.8rem', fontSize: '0.8rem' }}
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
