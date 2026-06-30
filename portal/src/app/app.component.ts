import { Component } from '@angular/core';

@Component({
  selector: 'app-root',
  template: `
    <nav class="navbar" *ngIf="authService.isLoggedIn()">
      <div class="navbar-brand">
        <span class="logo">⚡ WardWatch</span>
        <span class="portal-label">Official Portal</span>
      </div>
      <div class="navbar-info" *ngIf="authService.currentUser">
        <span class="official-name">{{ authService.currentUser.displayName || authService.currentUser.email }}</span>
        <button class="btn-logout" (click)="authService.logout()">Logout</button>
      </div>
    </nav>
    <main>
      <router-outlet></router-outlet>
    </main>
  `,
  styles: [`
    .navbar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 12px 24px;
      background: #1a1a2e;
      color: white;
      box-shadow: 0 2px 8px rgba(0,0,0,0.3);
    }
    .navbar-brand { display: flex; align-items: center; gap: 12px; }
    .logo { font-size: 20px; font-weight: 700; color: #e94560; }
    .portal-label { font-size: 12px; color: #aaa; background: #0f3460; padding: 2px 8px; border-radius: 4px; }
    .navbar-info { display: flex; align-items: center; gap: 16px; }
    .official-name { font-size: 14px; color: #ccc; }
    .btn-logout {
      padding: 6px 16px; border: 1px solid #e94560; background: transparent;
      color: #e94560; border-radius: 4px; cursor: pointer; font-size: 13px;
    }
    .btn-logout:hover { background: #e94560; color: white; }
    main { min-height: calc(100vh - 57px); background: #0f0f1a; }
  `]
})
export class AppComponent {
  constructor(public authService: AuthService) {}
}

import { AuthService } from './services/auth.service';
