import React from 'react';
import { NavLink } from 'react-router-dom';

const navigationItems = [
  {
    label: 'Dashboard',
    path: '/',
  },
  {
    label: 'Pull Requests',
    path: '/prs',
  },
  {
    label: 'History',
    path: '/history',
  },
  {
    label: 'Settings',
    path: '/settings',
  },
];

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="sidebar-section">
        <div className="sidebar-section-title">
          DeployGuard
        </div>

        <nav className="sidebar-nav" aria-label="Main navigation">
          {navigationItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === '/'}
              className={({ isActive }) =>
                `sidebar-link ${isActive ? 'active' : ''}`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </div>
    </aside>
  );
}