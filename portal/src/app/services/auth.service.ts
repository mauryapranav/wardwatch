/**
 * WardWatch - Auth Service (Angular)
 *
 * Handles Firebase Auth email/password login for the official portal.
 * After login, checks custom claims to ensure user has role='official'.
 * If not official, shows access denied and logs out.
 *
 * NOTE: Firebase Auth token is stored in-memory by Firebase SDK.
 * localStorage is used by Firebase SDK internally; this is acceptable
 * for a hackathon. Production should use httpOnly cookies.
 */
import { Injectable } from '@angular/core';
import { Router } from '@angular/router';
import { Auth, signInWithEmailAndPassword, signOut, onAuthStateChanged, User } from '@angular/fire/auth';
import { BehaviorSubject, Observable } from 'rxjs';

export interface OfficialUser {
  uid: string;
  email: string | null;
  displayName: string | null;
  role: string;
  wardId: string;
  idToken: string;
}

@Injectable({ providedIn: 'root' })
export class AuthService {
  currentUser: User | null = null;
  currentOfficialUser: OfficialUser | null = null;

  private _isLoggedIn = new BehaviorSubject<boolean>(false);
  isLoggedIn$ = this._isLoggedIn.asObservable();

  constructor(private auth: Auth, private router: Router) {
    // Listen to auth state changes
    onAuthStateChanged(this.auth, async (user) => {
      this.currentUser = user;
      if (user) {
        await this._loadClaims(user);
        this._isLoggedIn.next(true);
      } else {
        this.currentOfficialUser = null;
        this._isLoggedIn.next(false);
      }
    });
  }

  isLoggedIn(): boolean {
    return this._isLoggedIn.getValue();
  }

  /**
   * Login with email and password.
   * Returns null on success, error message string on failure.
   */
  async login(email: string, password: string): Promise<string | null> {
    try {
      const credential = await signInWithEmailAndPassword(this.auth, email, password);
      const user = credential.user;

      // Force-refresh token to get latest custom claims
      const idTokenResult = await user.getIdTokenResult(true);
      const claims = idTokenResult.claims;

      // Check role — must be 'official' or 'admin' to access portal
      if (claims['role'] !== 'official' && claims['admin'] !== true) {
        await signOut(this.auth);
        return 'Access denied. This portal is for verified officials only.';
      }

      this.currentOfficialUser = {
        uid: user.uid,
        email: user.email,
        displayName: user.displayName,
        role: String(claims['role'] || 'official'),
        wardId: String(claims['ward_id'] || ''),
        idToken: await user.getIdToken(),
      };

      this._isLoggedIn.next(true);
      return null;  // Success

    } catch (err: any) {
      // Return generic error messages — no Firebase internals exposed
      const code = err?.code || '';
      if (code === 'auth/user-not-found' || code === 'auth/wrong-password' || code === 'auth/invalid-credential') {
        return 'Invalid email or password. Please try again.';
      }
      if (code === 'auth/too-many-requests') {
        return 'Too many failed attempts. Please try again later.';
      }
      if (code === 'auth/user-disabled') {
        return 'This account has been disabled. Contact your administrator.';
      }
      return 'Login failed. Please check your connection and try again.';
    }
  }

  async logout(): Promise<void> {
    await signOut(this.auth);
    this.currentUser = null;
    this.currentOfficialUser = null;
    this._isLoggedIn.next(false);
    this.router.navigate(['/login']);
  }

  /**
   * Get the current Firebase ID token (force refresh).
   */
  async getIdToken(): Promise<string | null> {
    if (!this.currentUser) return null;
    try {
      return await this.currentUser.getIdToken(false);
    } catch {
      return null;
    }
  }

  private async _loadClaims(user: User): Promise<void> {
    try {
      const idTokenResult = await user.getIdTokenResult(false);
      const claims = idTokenResult.claims;
      this.currentOfficialUser = {
        uid: user.uid,
        email: user.email,
        displayName: user.displayName,
        role: String(claims['role'] || ''),
        wardId: String(claims['ward_id'] || ''),
        idToken: idTokenResult.token,
      };
    } catch {
      this.currentOfficialUser = null;
    }
  }
}
