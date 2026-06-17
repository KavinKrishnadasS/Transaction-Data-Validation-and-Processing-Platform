import React, { useState, useEffect } from 'react';
import UploadZone from './components/UploadZone';
import Scanner from './components/Scanner';
import Dashboard from './components/Dashboard';
// RulesConfig import removed

export default function App() {
  const [batches, setBatches] = useState([]);
  const [selectedBatch, setSelectedBatch] = useState(null);
  const [scanningBatch, setScanningBatch] = useState(null);
  const [loadingHistory, setLoadingHistory] = useState(false);

  // Determine backend URL: dynamic fallback for local development vs host deployments
  const backendUrl = import.meta.env.VITE_API_URL || 
    (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
      ? 'http://localhost:5000'
      : window.location.origin);

  const fetchBatchesHistory = async () => {
    setLoadingHistory(true);
    try {
      const res = await fetch(`${backendUrl}/api/batches`);
      if (res.ok) {
        const data = await res.json();
        setBatches(data);
      }
    } catch (err) {
      console.error("Error fetching upload history:", err);
    } finally {
      setLoadingHistory(false);
    }
  };

  useEffect(() => {
    fetchBatchesHistory();
  }, [backendUrl]);

  const handleUploadSuccess = (newBatch) => {
    // Refresh history
    fetchBatchesHistory();
    // Trigger scanning view
    setScanningBatch(newBatch);
    setSelectedBatch(null);
  };

  const handleScanComplete = async () => {
    if (scanningBatch) {
      try {
        const res = await fetch(`${backendUrl}/api/batches/${scanningBatch.id}`);
        if (res.ok) {
          const updatedBatch = await res.json();
          setSelectedBatch(updatedBatch);
        } else {
          setSelectedBatch(scanningBatch);
        }
      } catch (err) {
        console.error("Error fetching updated batch details:", err);
        setSelectedBatch(scanningBatch);
      }
      setScanningBatch(null);
      fetchBatchesHistory(); // refresh data sizes
    }
  };

  const selectPastBatch = (batch) => {
    if (batch.status === 'PENDING' || batch.status === 'VALIDATING') {
      setScanningBatch(batch);
      setSelectedBatch(null);
    } else {
      setSelectedBatch(batch);
      setScanningBatch(null);
    }
  };

  const handleDeleteBatch = async (batchId, e) => {
    e.stopPropagation();
    if (!window.confirm("Are you sure you want to delete this transaction audit log and its associated files?")) {
      return;
    }
    try {
      const res = await fetch(`${backendUrl}/api/batches/${batchId}`, {
        method: 'DELETE',
      });
      if (res.ok) {
        fetchBatchesHistory();
        if (selectedBatch && selectedBatch.id === batchId) {
          setSelectedBatch(null);
        }
      } else {
        alert("Failed to delete audit log.");
      }
    } catch (err) {
      console.error("Error deleting batch:", err);
      alert("Error deleting audit log.");
    }
  };

  const resetToUpload = () => {
    setSelectedBatch(null);
    setScanningBatch(null);
    fetchBatchesHistory();
  };

  return (
    <div className="app-container">
      {/* Premium Dark Header Nav */}
      <header className="app-header">
        <div className="logo-container" style={{ cursor: 'pointer' }} onClick={resetToUpload}>
          <h1 className="logo-text" style={{ fontSize: '1.25rem', fontWeight: '600', letterSpacing: '-0.01em' }}>
            Transaction data validation and processing platform
          </h1>
        </div>
      </header>

      {/* Main Workspace Layout */}
      <main className="app-content">
        {scanningBatch ? (
          <Scanner 
            batch={scanningBatch} 
            backendUrl={backendUrl} 
            onScanComplete={handleScanComplete} 
          />
        ) : selectedBatch ? (
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
              <div style={{ display: 'flex', gap: '0.75rem' }}>
                <button onClick={resetToUpload} className="btn btn-secondary" style={{ fontSize: '0.85rem' }}>
                  ← Back to Uploads
                </button>
                <button 
                  onClick={(e) => handleDeleteBatch(selectedBatch.id, e)} 
                  className="btn btn-secondary" 
                  style={{ 
                    fontSize: '0.85rem', 
                    backgroundColor: 'rgba(239, 68, 68, 0.1)', 
                    color: 'rgb(239, 68, 68)',
                    border: '1px solid rgba(239, 68, 68, 0.2)'
                  }}
                  title="Delete this audit log"
                >
                  🗑️ Delete Audit Log
                </button>
              </div>
              <h2 style={{ fontSize: '1.25rem', color: 'var(--ink-navy)' }}>
                Report: <span className="data-mono">{selectedBatch.filename}</span>
              </h2>
            </div>
            
            <Dashboard batch={selectedBatch} backendUrl={backendUrl} />
          </div>
        ) : (
          /* Standard Ingestion Workspace Landing */
          <>
            <UploadZone backendUrl={backendUrl} onUploadSuccess={handleUploadSuccess} />
            
            {/* Historical Batch Runs list */}
            <section className="history-section">
              <h3 style={{ borderBottom: '1px solid var(--gray-200)', paddingBottom: '0.5rem', marginBottom: '1rem' }}>
                Transaction Audit Logs
              </h3>

              {loadingHistory && batches.length === 0 ? (
                <div>Connecting to audit history...</div>
              ) : batches.length === 0 ? (
                <div className="empty-state">
                  <div className="empty-state-icon">📋</div>
                  <h4>Awaiting Ingestion</h4>
                  <p>No transaction datasets have been uploaded yet. Upload a CSV/XLSX file above to run validation audits.</p>
                </div>
              ) : (
                <div className="history-list">
                  {batches.map((b) => {
                    const dateObj = new Date(b.uploaded_at);
                    const formattedDate = dateObj.toLocaleDateString() + ' ' + dateObj.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                    
                    return (
                      <article 
                        key={b.id} 
                        onClick={() => selectPastBatch(b)}
                        className="history-item"
                        role="button"
                        tabIndex="0"
                        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') selectPastBatch(b); }}
                      >
                        <div className="history-item-meta">
                          <span className="history-filename">{b.filename}</span>
                          <span className="history-stats">
                            {b.status === 'COMPLETED' ? (
                              <>
                                <span>Total: <strong className="data-mono">{b.total_rows}</strong></span>
                                <span style={{ color: 'var(--teal-valid)' }}>Clean: <strong className="data-mono">{b.valid_rows}</strong></span>
                                <span style={{ color: b.error_rows > 0 ? 'var(--amber-flag)' : 'var(--gray-400)' }}>
                                  Flags: <strong className="data-mono">{b.error_rows}</strong>
                                </span>
                              </>
                            ) : b.status === 'FAILED' ? (
                              <span style={{ color: 'var(--amber-flag)' }}>Ingestion process failed</span>
                            ) : (
                              <span>Validation is processing in background...</span>
                            )}
                          </span>
                        </div>
                        
                        <div className="history-status" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                          <span className="history-date">{formattedDate}</span>
                          <span className={`status-indicator ${b.status.toLowerCase()}`}></span>
                          <span className="btn btn-secondary" style={{ fontSize: '0.75rem', padding: '0.25rem 0.5rem' }}>
                            {b.status === 'COMPLETED' ? 'View Dashboard' : b.status === 'VALIDATING' ? 'View Live Scan' : 'Review'}
                          </span>
                          <button 
                            onClick={(e) => handleDeleteBatch(b.id, e)} 
                            className="btn btn-secondary" 
                            style={{ 
                              fontSize: '0.75rem', 
                              padding: '0.25rem 0.5rem', 
                              backgroundColor: 'rgba(239, 68, 68, 0.1)', 
                              color: 'rgb(239, 68, 68)',
                              border: '1px solid rgba(239, 68, 68, 0.2)'
                            }}
                            title="Delete audit log"
                          >
                            🗑️
                          </button>
                        </div>
                      </article>
                    );
                  })}
                </div>
              )}
            </section>
          </>
        )}
      </main>
    </div>
  );
}
