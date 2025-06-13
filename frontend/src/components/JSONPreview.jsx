import React from 'react';
import { Eye, ChevronRight } from 'lucide-react';
import styles from './JSONPreview.module.css';

const JSONPreview = ({ data, onExpand, title = "JSON Response" }) => {
  const getPreviewText = (jsonData) => {
    if (!jsonData) return 'No data';
    
    if (typeof jsonData === 'string') {
      try {
        const parsed = JSON.parse(jsonData);
        return getPreviewText(parsed);
      } catch {
        return jsonData.length > 50 ? `${jsonData.substring(0, 50)}...` : jsonData;
      }
    }
    
    if (Array.isArray(jsonData)) {
      return `Array (${jsonData.length} items)`;
    }
    
    if (typeof jsonData === 'object' && jsonData !== null) {
      const keys = Object.keys(jsonData);
      if (keys.length === 0) return 'Empty object';
      
      const firstKey = keys[0];
      const preview = keys.length === 1 
        ? `{ "${firstKey}": ... }` 
        : `{ "${firstKey}": ..., +${keys.length - 1} more }`;
      
      return preview;
    }
    
    return String(jsonData);
  };

  const getDataSize = (jsonData) => {
    if (!jsonData) return '0 B';
    
    try {
      const jsonString = typeof jsonData === 'string' ? jsonData : JSON.stringify(jsonData);
      const bytes = new Blob([jsonString]).size;
      
      if (bytes < 1024) return `${bytes} B`;
      if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
      return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    } catch {
      return 'Unknown';
    }
  };

  return (
    <div className={styles.jsonPreview} onClick={(e) => {
      e.stopPropagation();
      onExpand && onExpand();
    }}>
      <div className={styles.previewHeader}>
        <div className={styles.headerLeft}>
          <Eye size={16} className={styles.icon} />
          <span className={styles.title}>{title}</span>
        </div>
        <div className={styles.headerRight}>
          <span className={styles.size}>{getDataSize(data)}</span>
          <ChevronRight size={16} className={styles.expandIcon} />
        </div>
      </div>
      
      <div className={styles.previewContent}>
        <code className={styles.previewText}>
          {getPreviewText(data)}
        </code>
      </div>
      
      <div className={styles.clickHint}>
        Click to view in detail
      </div>
    </div>
  );
};

export default JSONPreview; 