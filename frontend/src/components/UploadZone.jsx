import React, { useState, useRef } from 'react';

export default function UploadZone({ backendUrl, onUploadSuccess }) {
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const fileInputRef = useRef(null);

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    
    if (uploading) return;
    
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      processFile(files[0]);
    }
  };

  const handleFileChange = (e) => {
    const files = e.target.files;
    if (files.length > 0) {
      processFile(files[0]);
    }
  };

  const processFile = (file) => {
    setErrorMsg('');
    
    // Check file extension
    const extension = file.name.split('.').pop().lowerCase || file.name.split('.').pop().toLowerCase();
    const validExtensions = ['csv', 'xlsx', 'xls'];
    if (!validExtensions.includes(extension)) {
      setErrorMsg('Invalid file type. Only CSV, XLSX, and XLS files are supported.');
      return;
    }

    // Check file size (16 MB = 16 * 1024 * 1024 bytes)
    const maxSize = 16 * 1024 * 1024;
    if (file.size > maxSize) {
      setErrorMsg('File is too large. Maximum allowed size is 16MB.');
      return;
    }

    // Initiate upload
    uploadToServer(file);
  };

  const uploadToServer = async (file) => {
    setUploading(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch(`${backendUrl}/api/upload`, {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.error || 'Upload failed. Please try again.');
      }

      if (onUploadSuccess && data.batch) {
        onUploadSuccess(data.batch);
      }
    } catch (err) {
      setErrorMsg(err.message);
    } finally {
      setUploading(false);
    }
  };

  const triggerFileSelect = () => {
    if (!uploading) {
      fileInputRef.current.click();
    }
  };

  return (
    <section className="upload-card">
      <div 
        className={`upload-area ${isDragging ? 'dragging' : ''}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={triggerFileSelect}
        aria-label="Upload drag and drop area"
        role="button"
        tabIndex="0"
        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') triggerFileSelect(); }}
      >
        <input 
          type="file"
          ref={fileInputRef}
          onChange={handleFileChange}
          accept=".csv, .xlsx, .xls"
          style={{ display: 'none' }}
          id="file-upload-input"
        />
        <div className="upload-icon">
          {uploading ? '⏳' : '📤'}
        </div>
        <div className="upload-text">
          <h3>{uploading ? 'Processing transaction data...' : 'Drag & drop transactions file here'}</h3>
          <p>{uploading ? 'Uploading dataset and initializing rules validation engine...' : 'or click to browse local files'}</p>
          <div className="file-specs">Supports CSV, XLSX, or XLS formats (Max size: 16 MB)</div>
        </div>
      </div>
      
      {errorMsg && (
        <div style={{ marginTop: '1rem', color: 'var(--amber-flag)', fontSize: '0.9rem', fontWeight: '500' }}>
          ⚠️ {errorMsg}
        </div>
      )}

      <div className="upload-actions" style={{ justifyContent: 'center' }}>
        <button 
          onClick={triggerFileSelect}
          className="btn btn-primary"
          disabled={uploading}
        >
          {uploading ? 'Uploading...' : 'Browse Files'}
        </button>
      </div>
    </section>
  );
}
