import React from 'react';
import { Sun, Moon, Code, Home } from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { useNavigate, useLocation } from 'react-router-dom';
import styles from './Header.module.css';

const Header = () => {
  const { state, actions } = useApp();
  const navigate = useNavigate();
  const location = useLocation();

  const toggleTheme = () => {
    actions.setTheme(state.theme === 'light' ? 'dark' : 'light');
  };

  const handleHomeClick = () => {
    if (location.pathname !== '/') {
      actions.resetState();
      navigate('/');
    }
  };

  return (
    <header className={styles.header}>
      <div className="container">
        <div className={styles.headerContent}>
          <div className={styles.headerBrand} onClick={handleHomeClick}>
            <Code className={styles.brandIcon} />
            <span className={styles.brandText}>CGCM 2.0</span>
          </div>
          
          <nav className={styles.headerNav}>
            {location.pathname !== '/' && (
              <button 
                className={styles.navBtn} 
                onClick={handleHomeClick}
                title="Go to Home"
              >
                <Home size={20} />
                <span className={styles.navText}>Home</span>
              </button>
            )}
            
            <button 
              className={styles.themeToggle} 
              onClick={toggleTheme}
              title={`Switch to ${state.theme === 'light' ? 'dark' : 'light'} mode`}
            >
              {state.theme === 'light' ? <Moon size={20} /> : <Sun size={20} />}
            </button>
          </nav>
        </div>
      </div>
    </header>
  );
};

export default Header; 