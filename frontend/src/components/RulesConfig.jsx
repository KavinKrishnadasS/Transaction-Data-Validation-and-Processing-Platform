import React, { useState, useEffect } from 'react';

export default function RulesConfig({ backendUrl }) {
  const [rules, setRules] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  
  // Form state
  const [countryName, setCountryName] = useState('');
  const [countryCode, setCountryCode] = useState('');
  const [phoneLength, setPhoneLength] = useState('');
  const [phonePrefix, setPhonePrefix] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const fetchRules = async () => {
    try {
      setLoading(true);
      const res = await fetch(`${backendUrl}/api/rules`);
      if (!res.ok) throw new Error('Failed to load rules.');
      const data = await res.json();
      setRules(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRules();
  }, [backendUrl]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    
    if (!countryName || !countryCode || !phoneLength || !phonePrefix) {
      setError('All fields are required.');
      return;
    }

    setSubmitting(true);
    try {
      const res = await fetch(`${backendUrl}/api/rules`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          country_name: countryName,
          country_code: countryCode,
          phone_length: parseInt(phoneLength, 10),
          phone_prefix: phonePrefix
        })
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Failed to save rule.');

      setSuccess(data.message);
      
      // Clear form
      setCountryName('');
      setCountryCode('');
      setPhoneLength('');
      setPhonePrefix('');
      
      // Refresh list
      fetchRules();
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleEditSelect = (rule) => {
    setCountryName(rule.country_name);
    setCountryCode(rule.country_code);
    setPhoneLength(rule.phone_length.toString());
    setPhonePrefix(rule.phone_prefix);
  };

  return (
    <div className="rules-grid">
      {/* Rule Creator/Editor Form */}
      <form className="rule-form" onSubmit={handleSubmit}>
        <h3 style={{ borderBottom: '1px solid var(--gray-200)', paddingBottom: '0.75rem' }}>
          Configure Country Rule
        </h3>

        {error && (
          <div style={{ color: 'var(--amber-flag)', fontSize: '0.85rem', fontWeight: '500' }}>
            ⚠️ {error}
          </div>
        )}
        {success && (
          <div style={{ color: 'var(--teal-valid)', fontSize: '0.85rem', fontWeight: '500' }}>
            ✓ {success}
          </div>
        )}

        <div className="form-group">
          <label htmlFor="country-name-input">Country Name</label>
          <input 
            type="text" 
            id="country-name-input"
            placeholder="e.g. Singapore"
            value={countryName}
            onChange={(e) => setCountryName(e.target.value)}
            required
          />
        </div>

        <div className="form-group">
          <label htmlFor="country-code-input">Country Code (ISO 2-Letter)</label>
          <input 
            type="text" 
            id="country-code-input"
            placeholder="e.g. SG"
            maxLength="2"
            value={countryCode}
            onChange={(e) => setCountryCode(e.target.value.toUpperCase())}
            required
          />
        </div>

        <div className="form-group">
          <label htmlFor="phone-prefix-input">Phone Dialing Prefix</label>
          <input 
            type="text" 
            id="phone-prefix-input"
            placeholder="e.g. +65"
            value={phonePrefix}
            onChange={(e) => setPhonePrefix(e.target.value)}
            required
          />
          <span className="form-help">Include the + sign prefix if applicable</span>
        </div>

        <div className="form-group">
          <label htmlFor="phone-length-input">Local Number Digits (excluding prefix)</label>
          <input 
            type="number" 
            id="phone-length-input"
            placeholder="e.g. 8"
            min="4"
            max="15"
            value={phoneLength}
            onChange={(e) => setPhoneLength(e.target.value)}
            required
          />
        </div>

        <button 
          type="submit" 
          disabled={submitting} 
          className="btn btn-primary"
          style={{ width: '100%', justifyContent: 'center', marginTop: '0.5rem' }}
        >
          {submitting ? 'Saving Configuration...' : 'Apply Validation Rule'}
        </button>
      </form>

      {/* Active Rules List */}
      <div>
        <h3 style={{ marginBottom: '1.25rem' }}>Active Ingestion Configurations</h3>
        {loading ? (
          <div>Loading validation configuration rules...</div>
        ) : rules.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon">⚙️</div>
            <p>No phone validation rules configured. Standard fallback rule (7-15 digits) will apply.</p>
          </div>
        ) : (
          <div className="rules-list">
            {rules.map((rule) => (
              <article key={rule.id} className="rule-card">
                <div className="rule-card-info">
                  <h4>{rule.country_name}</h4>
                  <p>
                    Prefix: <span className="rule-badge">{rule.phone_prefix}</span>
                    <span style={{ margin: '0 0.5rem', color: 'var(--gray-300)' }}>|</span>
                    Expected Length: <span className="data-mono" style={{ fontWeight: '600' }}>{rule.phone_length}</span> digits
                  </p>
                </div>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <span className="rule-badge" style={{ backgroundColor: 'var(--ink-navy)', color: 'var(--white)' }}>
                    {rule.country_code}
                  </span>
                  <button 
                    onClick={() => handleEditSelect(rule)}
                    className="btn btn-secondary"
                    style={{ fontSize: '0.75rem', padding: '0.25rem 0.5rem' }}
                  >
                    Edit
                  </button>
                </div>
              </article>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
