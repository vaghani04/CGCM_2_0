import React, { useState, useEffect } from 'react';
import { X, ChevronDown, ChevronRight, Copy, Check } from 'lucide-react';
import styles from './JSONViewer.module.css';

const JSONViewer = ({ data, isOpen, onClose, title = "JSON Response" }) => {
  const [collapsed, setCollapsed] = useState({});
  const [copied, setCopied] = useState(false);

  // Reset collapsed state when data changes
  useEffect(() => {
    setCollapsed({});
  }, [data]);

  // Clear copied status after 2 seconds
  useEffect(() => {
    if (copied) {
      const timer = setTimeout(() => setCopied(false), 2000);
      return () => clearTimeout(timer);
    }
  }, [copied]);

  const toggleCollapse = (path) => {
    setCollapsed(prev => ({
      ...prev,
      [path]: !prev[path]
    }));
  };

  const copyToClipboard = async () => {
    try {
      const textToCopy = typeof data === 'string' ? data : JSON.stringify(data, null, 2);
      await navigator.clipboard.writeText(textToCopy);
      setCopied(true);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const renderValue = (value, key, path = '', level = 0) => {
    const currentPath = path ? `${path}.${key}` : key;
    const isCollapsed = collapsed[currentPath];
    
    if (value === null) {
      return <span className={styles.jsonNull}>null</span>;
    }
    
    if (typeof value === 'boolean') {
      return <span className={styles.jsonBoolean}>{value.toString()}</span>;
    }
    
    if (typeof value === 'number') {
      return <span className={styles.jsonNumber}>{value}</span>;
    }
    
    if (typeof value === 'string') {
      return <span className={styles.jsonString}>"{value}"</span>;
    }
    
    if (Array.isArray(value)) {
      if (value.length === 0) {
        return <span className={styles.jsonBracket}>[]</span>;
      }
      
      return (
        <div className={styles.jsonContainer}>
          <button 
            className={styles.jsonToggle}
            onClick={() => toggleCollapse(currentPath)}
            style={{ marginLeft: `${level * 20}px` }}
          >
            {isCollapsed ? <ChevronRight size={16} /> : <ChevronDown size={16} />}
            <span className={styles.jsonBracket}>[</span>
            {isCollapsed && (
              <span className={styles.jsonEllipsis}>... {value.length} items</span>
            )}
            {isCollapsed && <span className={styles.jsonBracket}>]</span>}
          </button>
          
          {!isCollapsed && (
            <div className={styles.jsonContent}>
              {value.map((item, index) => (
                <div key={index} className={styles.jsonItem}>
                  <span className={styles.jsonIndex}>{index}:</span>
                  {renderValue(item, index, currentPath, level + 1)}
                  {index < value.length - 1 && <span className={styles.jsonComma}>,</span>}
                </div>
              ))}
              <div style={{ marginLeft: `${level * 20}px` }}>
                <span className={styles.jsonBracket}>]</span>
              </div>
            </div>
          )}
        </div>
      );
    }
    
    if (typeof value === 'object') {
      const keys = Object.keys(value);
      if (keys.length === 0) {
        return <span className={styles.jsonBracket}>{}</span>;
      }
      
      return (
        <div className={styles.jsonContainer}>
          <button 
            className={styles.jsonToggle}
            onClick={() => toggleCollapse(currentPath)}
            style={{ marginLeft: `${level * 20}px` }}
          >
            {isCollapsed ? <ChevronRight size={16} /> : <ChevronDown size={16} />}
            <span className={styles.jsonBracket}>{"{"}</span>
            {isCollapsed && (
              <span className={styles.jsonEllipsis}>... {keys.length} properties</span>
            )}
            {isCollapsed && <span className={styles.jsonBracket}>{"}"}</span>}
          </button>
          
          {!isCollapsed && (
            <div className={styles.jsonContent}>
              {keys.map((objKey, index) => (
                <div key={objKey} className={styles.jsonItem}>
                  <span className={styles.jsonKey}>"{objKey}":</span>
                  {renderValue(value[objKey], objKey, currentPath, level + 1)}
                  {index < keys.length - 1 && <span className={styles.jsonComma}>,</span>}
                </div>
              ))}
              <div style={{ marginLeft: `${level * 20}px` }}>
                <span className={styles.jsonBracket}>{"}"}</span>
              </div>
            </div>
          )}
        </div>
      );
    }
    
    return <span>{String(value)}</span>;
  };

  if (!isOpen) return null;

  return (
    <>
      {/* JSON Viewer Canvas - No backdrop for split-screen functionality */}
      <div className={`${styles.jsonViewer} ${isOpen ? styles.open : ''}`}>
        <div className={styles.header}>
          <h2 className={styles.title}>{title}</h2>
          <div className={styles.headerActions}>
            <button
              className={styles.copyButton}
              onClick={copyToClipboard}
              title="Copy JSON"
            >
              {copied ? <Check size={18} /> : <Copy size={18} />}
              {copied ? 'Copied!' : 'Copy'}
            </button>
            <button
              className={styles.closeButton}
              onClick={onClose}
              title="Close viewer"
            >
              <X size={20} />
            </button>
          </div>
        </div>
        
        <div className={styles.content}>
          <div className={styles.jsonDisplay}>
            {data ? renderValue(data, 'root') : (
              <div className={styles.noData}>No data to display</div>
            )}
          </div>
        </div>
      </div>
    </>
  );
};

export default JSONViewer; 