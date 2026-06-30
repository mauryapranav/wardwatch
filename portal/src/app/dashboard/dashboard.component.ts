/**
 * WardWatch - Official Dashboard (Step 3.4)
 *
 * Fetches issues from GET /api/v1/officials/{id}/issues on load.
 * Table: Campaign ID, Title, Type, Severity, Citizens, Status, SLA Countdown.
 * SLA Countdown: red if < 24h, "OVERDUE" if expired.
 * Status badges with colored chips.
 * Row click navigates to issue detail.
 * Auto-refresh every 60 seconds.
 */
import { Component, OnInit, OnDestroy } from '@angular/core';
import { Router } from '@angular/router';
import { interval, Subscription } from 'rxjs';
import { AuthService } from '../services/auth.service';
import { ApiService, OfficialIssue } from '../services/api.service';

@Component({
  selector: 'app-dashboard',
  template: `
    <div class="dashboard">
      <!-- Header -->
      <div class="dash-header">
        <div class="header-left">
          <h2 class="page-title">My Issues</h2>
          <span class="ward-badge" *ngIf="wardId">Ward: {{ wardId }}</span>
        </div>
        <div class="header-right">
          <span class="refresh-indicator" *ngIf="isLoading">
            <span class="spinner-sm"></span> Refreshing...
          </span>
          <span class="last-refreshed" *ngIf="lastRefreshed">
            Last updated: {{ lastRefreshed }}
          </span>
        </div>
      </div>

      <!-- Error State -->
      <div class="alert alert-error" *ngIf="errorMessage">
        <span>⚠️</span>
        <p>{{ errorMessage }}</p>
      </div>

      <!-- Loading State (initial load only) -->
      <div class="loading-state" *ngIf="isLoading && issues.length === 0">
        <div class="spinner-lg"></div>
        <p>Loading your issues...</p>
      </div>

      <!-- Empty State -->
      <div class="empty-state" *ngIf="!isLoading && issues.length === 0 && !errorMessage">
        <div class="empty-icon">✅</div>
        <h3>All Clear!</h3>
        <p>No active issues assigned to you or your ward.</p>
      </div>

      <!-- Issues Table -->
      <div class="table-wrapper" *ngIf="issues.length > 0">
        <table class="issues-table">
          <thead>
            <tr>
              <th>Campaign ID</th>
              <th>Title</th>
              <th>Type</th>
              <th>Sev.</th>
              <th>Citizens</th>
              <th>Status</th>
              <th>SLA Countdown</th>
            </tr>
          </thead>
          <tbody>
            <tr
              *ngFor="let issue of issues"
              class="table-row"
              (click)="openIssue(issue.campaign_id)"
            >
              <td class="campaign-id">#{{ issue.campaign_id.slice(-6).toUpperCase() }}</td>
              <td class="title-cell" [title]="issue.title">{{ truncate(issue.title, 45) }}</td>
              <td>
                <span class="type-badge type-{{ issue.issue_type }}">
                  {{ getTypeIcon(issue.issue_type) }} {{ issue.issue_type }}
                </span>
              </td>
              <td>
                <span class="severity-badge sev-{{ issue.severity }}">{{ issue.severity }}/5</span>
              </td>
              <td class="citizens">{{ issue.citizen_count }}</td>
              <td>
                <span class="status-badge status-{{ issue.status }}">
                  {{ getStatusLabel(issue.status) }}
                </span>
              </td>
              <td>
                <span [ngClass]="getSlaClass(issue.sla_deadline)">
                  {{ getSlaLabel(issue.sla_deadline) }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <p class="table-note" *ngIf="issues.length > 0">
        {{ issues.length }} active issue(s). Click any row to view details. Auto-refreshes every 60 seconds.
      </p>
    </div>
  `,
  styles: [`
    .dashboard {
      padding: 24px 32px;
      max-width: 1400px;
      margin: 0 auto;
      color: white;
    }
    .dash-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 24px;
    }
    .header-left { display: flex; align-items: center; gap: 12px; }
    .page-title { font-size: 24px; font-weight: 700; color: white; margin: 0; }
    .ward-badge {
      background: #0f3460; color: #64b5f6; padding: 4px 12px;
      border-radius: 20px; font-size: 12px; font-weight: 600;
    }
    .header-right { display: flex; align-items: center; gap: 16px; }
    .refresh-indicator { color: #888; font-size: 13px; display: flex; align-items: center; gap: 6px; }
    .last-refreshed { color: #555; font-size: 12px; }
    .alert { display: flex; gap: 12px; align-items: center; padding: 12px 16px; border-radius: 8px; margin-bottom: 20px; }
    .alert-error { background: rgba(233, 69, 96, 0.15); border: 1px solid rgba(233, 69, 96, 0.3); }
    .alert p { margin: 0; color: #ff8fa3; font-size: 14px; }
    .loading-state {
      display: flex; flex-direction: column; align-items: center;
      justify-content: center; padding: 80px; color: #888;
    }
    .loading-state p { margin-top: 16px; }
    .empty-state {
      text-align: center; padding: 80px;
    }
    .empty-icon { font-size: 48px; margin-bottom: 16px; }
    .empty-state h3 { color: white; margin-bottom: 8px; }
    .empty-state p { color: #888; }
    .spinner-sm {
      width: 14px; height: 14px;
      border: 2px solid rgba(255,255,255,0.2);
      border-top-color: #e94560;
      border-radius: 50%;
      animation: spin 0.6s linear infinite;
      display: inline-block;
    }
    .spinner-lg {
      width: 40px; height: 40px;
      border: 3px solid rgba(255,255,255,0.1);
      border-top-color: #e94560;
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
    }
    @keyframes spin { to { transform: rotate(360deg); } }
    .table-wrapper { overflow-x: auto; border-radius: 12px; }
    .issues-table {
      width: 100%;
      border-collapse: collapse;
      background: rgba(255,255,255,0.03);
      border: 1px solid rgba(255,255,255,0.08);
    }
    thead { background: rgba(255,255,255,0.06); }
    th {
      padding: 14px 16px; text-align: left; font-size: 11px; font-weight: 700;
      text-transform: uppercase; letter-spacing: 0.8px; color: #888;
      border-bottom: 1px solid rgba(255,255,255,0.08);
    }
    .table-row {
      border-bottom: 1px solid rgba(255,255,255,0.05);
      cursor: pointer;
      transition: background 0.15s;
    }
    .table-row:hover { background: rgba(233, 69, 96, 0.08); }
    td { padding: 14px 16px; font-size: 14px; color: #ddd; vertical-align: middle; }
    .campaign-id { font-family: monospace; color: #64b5f6; font-size: 13px; }
    .title-cell { max-width: 250px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .type-badge {
      padding: 3px 10px; border-radius: 12px; font-size: 11px; font-weight: 600;
      text-transform: capitalize; white-space: nowrap;
    }
    .type-pothole { background: rgba(244,67,54,0.2); color: #f44336; }
    .type-streetlight { background: rgba(255,193,7,0.2); color: #ffc107; }
    .type-water { background: rgba(33,150,243,0.2); color: #2196f3; }
    .type-garbage { background: rgba(76,175,80,0.2); color: #4caf50; }
    .type-sidewalk { background: rgba(255,152,0,0.2); color: #ff9800; }
    .type-other { background: rgba(158,158,158,0.2); color: #9e9e9e; }
    .severity-badge {
      padding: 3px 8px; border-radius: 4px; font-size: 12px; font-weight: 700;
    }
    .sev-1, .sev-2 { background: rgba(76,175,80,0.2); color: #81c784; }
    .sev-3 { background: rgba(255,152,0,0.2); color: #ffb74d; }
    .sev-4, .sev-5 { background: rgba(244,67,54,0.2); color: #e57373; }
    .citizens { font-weight: 600; color: white; text-align: center; }
    .status-badge {
      padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: 700;
      text-transform: uppercase; letter-spacing: 0.5px; white-space: nowrap;
    }
    .status-open { background: rgba(158,158,158,0.2); color: #bdbdbd; }
    .status-acknowledged_pending { background: rgba(33,150,243,0.2); color: #64b5f6; }
    .status-acknowledged { background: rgba(33,150,243,0.25); color: #90caf9; }
    .status-in_progress { background: rgba(255,193,7,0.2); color: #ffd54f; }
    .status-resolved { background: rgba(76,175,80,0.2); color: #81c784; }
    .status-verifying { background: rgba(156,39,176,0.2); color: #ce93d8; }
    .status-closed { background: rgba(76,175,80,0.25); color: #a5d6a7; }
    .status-reopened { background: rgba(255,152,0,0.2); color: #ffcc80; }
    .status-escalated { background: rgba(244,67,54,0.25); color: #ef9a9a; }
    .sla-ok { color: #81c784; font-weight: 600; font-size: 13px; }
    .sla-warning { color: #ffd54f; font-weight: 600; font-size: 13px; }
    .sla-critical { color: #ff7043; font-weight: 700; font-size: 13px; }
    .sla-overdue { color: #f44336; font-weight: 800; font-size: 13px; animation: blink 1s infinite; }
    @keyframes blink { 50% { opacity: 0.6; } }
    .sla-none { color: #555; font-size: 13px; }
    .table-note { color: #555; font-size: 12px; margin-top: 12px; }
  `]
})
export class DashboardComponent implements OnInit, OnDestroy {
  issues: OfficialIssue[] = [];
  isLoading = false;
  errorMessage = '';
  lastRefreshed = '';
  wardId = '';

  private refreshSub?: Subscription;

  constructor(
    private router: Router,
    private authService: AuthService,
    private apiService: ApiService
  ) {}

  ngOnInit(): void {
    const user = this.authService.currentOfficialUser;
    if (user) {
      this.wardId = user.wardId;
    }
    this.loadIssues();
    // Auto-refresh every 60 seconds
    this.refreshSub = interval(60000).subscribe(() => this.loadIssues());
  }

  ngOnDestroy(): void {
    this.refreshSub?.unsubscribe();
  }

  loadIssues(): void {
    const user = this.authService.currentOfficialUser;
    if (!user) return;

    this.isLoading = true;
    this.errorMessage = '';

    this.apiService.getOfficialIssues(user.uid).subscribe({
      next: (data) => {
        this.issues = data;
        this.isLoading = false;
        this.lastRefreshed = new Date().toLocaleTimeString();
      },
      error: (err) => {
        this.isLoading = false;
        if (err.status === 401) {
          this.authService.logout();
        } else if (err.status === 403) {
          this.errorMessage = 'Access denied.';
        } else {
          this.errorMessage = 'Failed to load issues. Please refresh the page.';
        }
      }
    });
  }

  openIssue(campaignId: string): void {
    this.router.navigate(['/issues', campaignId]);
  }

  truncate(text: string, max: number): string {
    return text.length > max ? text.slice(0, max) + '...' : text;
  }

  getTypeIcon(type: string): string {
    const icons: Record<string, string> = {
      pothole: '🕳️', streetlight: '💡', water: '💧',
      garbage: '🗑️', sidewalk: '🚶', other: '⚠️'
    };
    return icons[type] || '⚠️';
  }

  getStatusLabel(st: string): string {
    const labels: Record<string, string> = {
      open: 'Open',
      acknowledged_pending: 'Pending',
      acknowledged: 'Acknowledged',
      in_progress: 'In Progress',
      resolved: 'Resolved',
      verifying: 'Verifying',
      closed: 'Closed',
      reopened: 'Reopened',
      escalated: 'Escalated',
    };
    return labels[st] || st;
  }

  getSlaClass(sla: string | null): string {
    if (!sla) return 'sla-none';
    const deadline = new Date(sla);
    const now = new Date();
    const diffMs = deadline.getTime() - now.getTime();
    if (diffMs < 0) return 'sla-overdue';
    if (diffMs < 24 * 3600 * 1000) return 'sla-critical';
    if (diffMs < 48 * 3600 * 1000) return 'sla-warning';
    return 'sla-ok';
  }

  getSlaLabel(sla: string | null): string {
    if (!sla) return '—';
    const deadline = new Date(sla);
    const now = new Date();
    const diffMs = deadline.getTime() - now.getTime();
    if (diffMs < 0) return '⚠️ OVERDUE';
    const days = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    const hours = Math.floor((diffMs % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
    if (days > 0) return `${days}d ${hours}h`;
    return `${hours}h remaining`;
  }
}
