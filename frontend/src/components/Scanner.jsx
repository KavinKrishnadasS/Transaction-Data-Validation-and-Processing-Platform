import React, { useState, useEffect, useRef } from 'react';

export default function Scanner({ batch, backendUrl, onScanComplete }) {
  const [transactions, setTransactions] = useState([]);
  const [scannedIndex, setScannedIndex] = useState(-1);
  const [batchStatus, setBatchStatus] = useState(batch.status);
  const [metrics, setMetrics] = useState({ total: 0, valid: 0, error: 0 });
  const viewportRef = useRef(null);
  const intervalRef = useRef(null);
  const rowRefs = useRef([]);

  // Check user preference for motion
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // Poll batch status from server
  useEffect(() => {
    let pollInterval = setInterval(async () => {
      try {
        const res = await fetch(`${backendUrl}/api/batches/${batch.id}`);
        if (!res.ok) return;
        const data = await res.json();
        setBatchStatus(data.status);
        setMetrics({
          total: data.total_rows,
          valid: data.valid_rows,
          error: data.error_rows
        });

        if (data.status === 'COMPLETED' || data.status === 'FAILED') {
          clearInterval(pollInterval);
        }
      } catch (err) {
        console.error("Error polling batch status:", err);
      }
    }, 1500);

    return () => clearInterval(pollInterval);
  }, [batch.id, backendUrl]);

  // Load transactions to scan
  useEffect(() => {
    let isMounted = true;
    const fetchTransactions = async () => {
      try {
        const res = await fetch(`${backendUrl}/api/batches/${batch.id}/transactions?per_page=100`);
        if (!res.ok) return;
        const data = await res.json();
        if (isMounted) {
          setTransactions(data.transactions);
          // If reduced motion is requested, instantly scan all loaded rows
          if (prefersReducedMotion) {
            setScannedIndex(data.transactions.length - 1);
          }
        }
      } catch (err) {
        console.error("Error loading transactions for scan:", err);
      }
    };

    fetchTransactions();
    // Re-fetch transactions periodically while validating to show incoming rows
    const interval = setInterval(() => {
      if (batchStatus === 'VALIDATING' || batchStatus === 'PENDING') {
        fetchTransactions();
      } else {
        clearInterval(interval);
      }
    }, 2000);

    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [batch.id, backendUrl, batchStatus, prefersReducedMotion]);

  // Handle sequential row reveal animation
  useEffect(() => {
    if (transactions.length === 0 || prefersReducedMotion) return;

    if (intervalRef.current) clearInterval(intervalRef.current);

    intervalRef.current = setInterval(() => {
      setScannedIndex((prevIndex) => {
        if (prevIndex < transactions.length - 1) {
          return prevIndex + 1;
        } else {
          // If we reached the end of currently loaded rows, check if batch is finished
          if (batchStatus === 'COMPLETED' || batchStatus === 'FAILED') {
            clearInterval(intervalRef.current);
            // Settle and finish scan flow after small delay
            setTimeout(() => {
              onScanComplete();
            }, 1000);
          }
          return prevIndex;
        }
      });
    }, 120); // 120ms per row scanning speed

    return () => clearInterval(intervalRef.current);
  }, [transactions.length, batchStatus, onScanComplete, prefersReducedMotion]);

  // Auto-scroll the viewport to keep the active scanner row centered
  useEffect(() => {
    if (scannedIndex >= 0 && rowRefs.current[scannedIndex] && viewportRef.current) {
      const viewport = viewportRef.current;
      const activeRow = rowRefs.current[scannedIndex];
      
      const viewportHeight = viewport.clientHeight;
      const rowOffsetTop = activeRow.offsetTop;
      const rowHeight = activeRow.clientHeight;
      
      viewport.scrollTo({
        top: rowOffsetTop - (viewportHeight / 2) + (rowHeight / 2),
        behavior: prefersReducedMotion ? 'auto' : 'smooth'
      });
    }
  }, [scannedIndex, prefersReducedMotion]);

  // Instant skip button handler
  const handleSkip = () => {
    onScanComplete();
  };

  return (
    <section className="scanner-card">
      <div className="scanner-title">
        <div>
          <h2 style={{ color: 'var(--white)' }}>Security Checkpoint: Ingestion Scan</h2>
          <p style={{ color: 'var(--gray-400)', fontSize: '0.9rem', marginTop: '0.25rem' }}>
            File: <span className="data-mono" style={{ color: 'var(--white)' }}>{batch.filename}</span>
          </p>
        </div>
        <div style={{ textAlign: 'right' }}>
          <span className="status-badge flagged" style={{ animation: 'pulse 1.5s infinite', marginRight: '1rem' }}>
            {batchStatus}
          </span>
          <button onClick={handleSkip} className="btn btn-secondary" style={{ fontSize: '0.8rem', padding: '0.4rem 0.8rem' }}>
            Skip Animation
          </button>
        </div>
      </div>

      <div className="scanner-viewport" ref={viewportRef}>
        {!prefersReducedMotion && <div className="scan-line"></div>}
        
        {transactions.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '4rem 1rem', color: 'var(--gray-400)' }}>
            Initializing connection stream. Awaiting records...
          </div>
        ) : (
          <div className="scanner-rows">
            {transactions.map((tx, idx) => {
              let rowState = 'pending'; // pending, validating, valid, flagged
              let rowText = 'Awaiting sweep...';
              
              if (idx === scannedIndex) {
                rowState = 'validating';
                rowText = 'Analyzing cell data...';
              } else if (idx < scannedIndex) {
                rowState = tx.is_valid ? 'valid' : 'flagged';
                rowText = tx.is_valid ? 'Verification Passed' : 'Validation Flagged';
              }

              return (
                <div 
                  key={tx.id} 
                  ref={el => rowRefs.current[idx] = el}
                  className={`scanner-row ${rowState}`}
                >
                  <div className="scanner-row-info">
                    <span className="scanner-cell scanner-cell-id data-mono">#{tx.row_number}</span>
                    {Object.entries(tx.raw_data || {}).slice(0, 3).map(([key, value]) => (
                      <span key={key} className="scanner-cell" style={{ width: '130px' }}>
                        <span style={{ fontSize: '0.7rem', color: 'var(--gray-400)', display: 'block', textTransform: 'uppercase' }}>{key}</span>
                        {value !== null && value !== undefined ? String(value) : 'N/A'}
                      </span>
                    ))}
                    {rowState === 'flagged' && (
                      <span className="scanner-cell scanner-cell-error" style={{ flex: 1 }}>
                        ⚠️ Data Integrity Issue Detected
                      </span>
                    )}
                  </div>
                  
                  <div>
                    {rowState === 'valid' && (
                      <span className="status-badge valid" style={{ fontFamily: 'var(--font-mono)' }}>✓ VALID</span>
                    )}
                    {rowState === 'flagged' && (
                      <span className="status-badge flagged" style={{ fontFamily: 'var(--font-mono)' }}>✗ FLAGGED</span>
                    )}
                    {rowState === 'validating' && (
                      <span className="status-badge" style={{ backgroundColor: 'rgba(47, 111, 237, 0.2)', color: 'var(--signal-blue)', fontFamily: 'var(--font-mono)' }}>SCANNING</span>
                    )}
                    {rowState === 'pending' && (
                      <span className="status-badge scan-pending" style={{ fontFamily: 'var(--font-mono)' }}>QUEUE</span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      <div style={{ marginTop: '1.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div className="data-mono" style={{ fontSize: '0.85rem', color: 'var(--gray-300)' }}>
          Processed: {scannedIndex + 1} / {transactions.length} loaded records
        </div>
        
        {batchStatus === 'COMPLETED' && scannedIndex >= transactions.length - 1 && (
          <div style={{ color: 'var(--teal-valid)', fontWeight: '600', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            🎉 Audit scan complete. Generating final audit reports...
          </div>
        )}
      </div>
    </section>
  );
}
