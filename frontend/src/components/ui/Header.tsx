import React from 'react';
import { Link } from 'react-router-dom';
import Icon from './Icon';

export default function Header() {
  return (
    <header className="app-header">
      <div className="app-header-left">
        <Link
          to="/"
          className="logo"
          aria-label="DeployGuard Dashboard"
        >
          DeployGuard
        </Link>

        <span className="header-divider" />

        <span className="header-context">
          Deployment Intelligence
        </span>
      </div>

      <div className="app-header-right">
        <div className="header-status">
          <span className="header-status-dot" />
          <span>System Operational</span>
        </div>

        <Link
          to="/settings"
          className="header-settings"
          aria-label="Settings"
        >
          <Icon name="cog" />
        </Link>
      </div>
    </header>
  );
}