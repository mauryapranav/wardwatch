import { Injectable } from '@angular/core';
import { CanActivate, Router } from '@angular/router';
import { AuthService } from '../services/auth.service';

@Injectable({ providedIn: 'root' })
export class OfficialGuard implements CanActivate {
  constructor(private authService: AuthService, private router: Router) {}

  canActivate(): boolean {
    const user = this.authService.currentOfficialUser;
    if (user && (user.role === 'official' || user.role === 'ward_engineer' || user.role === 'admin')) {
      return true;
    }
    // Not an official — logout and redirect
    this.authService.logout();
    return false;
  }
}
