/**
 * WardWatch - Official Login Component (Step 3.2)
 *
 * Email/password Firebase Auth login for official portal.
 * After login, checks custom claims: if role !== 'official', shows access denied and logs out.
 *
 * NOTE (hackathon): Firebase stores the auth token in localStorage internally.
 * Production should use httpOnly session cookies via a backend endpoint.
 */
import { Component } from '@angular/core';
import { Router } from '@angular/router';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';
import { AuthService } from '../services/auth.service';

@Component({
  selector: 'app-login',
  template: `
    <div class="login-wrapper">
      <div class="login-card">
        <!-- Logo -->
        <div class="brand">
          <span class="brand-icon">⚡</span>
          <h1 class="brand-name">WardWatch</h1>
          <p class="brand-sub">Official Portal</p>
        </div>

        <!-- Access Denied Banner -->
        <div class="alert alert-error" *ngIf="accessDenied">
          <span class="alert-icon">🚫</span>
          <div>
            <strong>Access Denied</strong>
            <p>This portal is for verified officials only. Your account does not have the required permissions.</p>
          </div>
        </div>

        <!-- Login Form -->
        <form [formGroup]="loginForm" (ngSubmit)="onSubmit()" *ngIf="!accessDenied">
          <div class="form-group">
            <label for="email">Official Email</label>
            <input
              id="email"
              type="email"
              formControlName="email"
              placeholder="your.name@municipal.gov.in"
              autocomplete="email"
              [class.invalid]="isFieldInvalid('email')"
            />
            <span class="field-error" *ngIf="isFieldInvalid('email')">
              Please enter a valid email address.
            </span>
          </div>

          <div class="form-group">
            <label for="password">Password</label>
            <input
              id="password"
              type="password"
              formControlName="password"
              placeholder="Enter your password"
              autocomplete="current-password"
              [class.invalid]="isFieldInvalid('password')"
            />
            <span class="field-error" *ngIf="isFieldInvalid('password')">
              Password is required.
            </span>
          </div>

          <!-- Error Message -->
          <div class="alert alert-error" *ngIf="errorMessage">
            <span class="alert-icon">⚠️</span>
            <p>{{ errorMessage }}</p>
          </div>

          <!-- Submit Button -->
          <button
            type="submit"
            class="btn-primary"
            [disabled]="isLoading || loginForm.invalid"
          >
            <span class="spinner" *ngIf="isLoading"></span>
            <span *ngIf="!isLoading">Sign In</span>
            <span *ngIf="isLoading">Signing in...</span>
          </button>
        </form>

        <!-- Contact Admin (for access denied) -->
        <div class="contact-admin" *ngIf="accessDenied">
          <button class="btn-secondary" (click)="tryAgain()">Try Another Account</button>
          <p class="help-text">
            If you believe this is an error, contact your administrator to verify your official account.
          </p>
        </div>

        <p class="portal-note">
          This portal is for registered municipal officials only. Citizens should use the WardWatch mobile app.
        </p>
      </div>
    </div>
  `,
  styles: [`
    .login-wrapper {
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      background: linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 50%, #0f3460 100%);
    }
    .login-card {
      background: rgba(255, 255, 255, 0.05);
      backdrop-filter: blur(20px);
      border: 1px solid rgba(255, 255, 255, 0.1);
      border-radius: 16px;
      padding: 48px 40px;
      width: 100%;
      max-width: 420px;
      box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
    }
    .brand {
      text-align: center;
      margin-bottom: 32px;
    }
    .brand-icon { font-size: 40px; }
    .brand-name {
      font-size: 28px;
      font-weight: 800;
      color: #e94560;
      margin: 8px 0 4px;
      letter-spacing: -0.5px;
    }
    .brand-sub {
      font-size: 13px;
      color: #888;
      background: #0f3460;
      display: inline-block;
      padding: 2px 12px;
      border-radius: 20px;
      margin: 0;
    }
    .form-group {
      margin-bottom: 20px;
    }
    label {
      display: block;
      color: #ccc;
      font-size: 13px;
      font-weight: 600;
      margin-bottom: 6px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }
    input {
      width: 100%;
      padding: 12px 16px;
      background: rgba(255, 255, 255, 0.07);
      border: 1px solid rgba(255, 255, 255, 0.15);
      border-radius: 8px;
      color: white;
      font-size: 15px;
      transition: border-color 0.2s;
      box-sizing: border-box;
    }
    input:focus {
      outline: none;
      border-color: #e94560;
      background: rgba(255, 255, 255, 0.1);
    }
    input.invalid { border-color: #ff6b6b; }
    input::placeholder { color: #555; }
    .field-error { color: #ff6b6b; font-size: 12px; margin-top: 4px; display: block; }
    .alert {
      display: flex;
      align-items: flex-start;
      gap: 12px;
      padding: 12px 16px;
      border-radius: 8px;
      margin-bottom: 20px;
    }
    .alert-error { background: rgba(233, 69, 96, 0.15); border: 1px solid rgba(233, 69, 96, 0.3); }
    .alert-icon { font-size: 18px; flex-shrink: 0; }
    .alert p { margin: 0; color: #ff8fa3; font-size: 14px; }
    .alert strong { color: #ff8fa3; display: block; margin-bottom: 4px; }
    .btn-primary {
      width: 100%;
      padding: 14px;
      background: linear-gradient(135deg, #e94560, #c2185b);
      color: white;
      border: none;
      border-radius: 8px;
      font-size: 16px;
      font-weight: 600;
      cursor: pointer;
      transition: opacity 0.2s, transform 0.1s;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
    }
    .btn-primary:hover:not(:disabled) { opacity: 0.9; transform: translateY(-1px); }
    .btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
    .btn-secondary {
      width: 100%;
      padding: 12px;
      background: transparent;
      color: #e94560;
      border: 1px solid #e94560;
      border-radius: 8px;
      font-size: 14px;
      cursor: pointer;
      margin-bottom: 12px;
    }
    .btn-secondary:hover { background: rgba(233, 69, 96, 0.1); }
    .spinner {
      width: 18px; height: 18px;
      border: 2px solid rgba(255,255,255,0.3);
      border-top-color: white;
      border-radius: 50%;
      animation: spin 0.6s linear infinite;
      display: inline-block;
    }
    @keyframes spin { to { transform: rotate(360deg); } }
    .contact-admin { margin-top: 24px; }
    .help-text { color: #777; font-size: 12px; text-align: center; margin: 0; }
    .portal-note {
      text-align: center;
      color: #555;
      font-size: 11px;
      margin-top: 24px;
      margin-bottom: 0;
      line-height: 1.5;
    }
  `]
})
export class LoginComponent {
  loginForm: FormGroup;
  isLoading = false;
  errorMessage = '';
  accessDenied = false;

  constructor(
    private fb: FormBuilder,
    private authService: AuthService,
    private router: Router
  ) {
    this.loginForm = this.fb.group({
      email: ['', [Validators.required, Validators.email]],
      password: ['', [Validators.required, Validators.minLength(6)]],
    });

    // If already logged in as official, go to dashboard
    if (this.authService.isLoggedIn()) {
      this.router.navigate(['/dashboard']);
    }
  }

  isFieldInvalid(field: string): boolean {
    const control = this.loginForm.get(field);
    return !!(control && control.invalid && (control.dirty || control.touched));
  }

  async onSubmit(): Promise<void> {
    if (this.loginForm.invalid) return;

    this.isLoading = true;
    this.errorMessage = '';
    this.accessDenied = false;

    const { email, password } = this.loginForm.value;
    const error = await this.authService.login(email, password);

    this.isLoading = false;

    if (error === null) {
      // Success — navigate to dashboard
      this.router.navigate(['/dashboard']);
    } else if (error.includes('Access denied')) {
      this.accessDenied = true;
    } else {
      this.errorMessage = error;
    }
  }

  tryAgain(): void {
    this.accessDenied = false;
    this.errorMessage = '';
    this.loginForm.reset();
  }
}
