/**
 * WardWatch - Issue Detail Page (Step 3.6)
 *
 * Receives campaign_id from route parameters.
 * Fetches campaign details from GET /api/v1/issues/{id}.
 * Shows photos, title, description, issue type, severity, citizen count, status, timeline, address.
 * Status update buttons: Acknowledge, In Progress, Resolved, Request More Info.
 * Confirmation dialog before Resolved (triggers verifying).
 * Refreshes data after each update.
 */
import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { AuthService } from '../services/auth.service';
import { ApiService, CampaignDetail, TimelineEvent } from '../services/api.service';

@Component({
  selector: 'app-issue-detail',
  template: `
    <div class="detail-page">
      <!-- Back Button -->
      <button class="btn-back" (click)="goBack()">← Back to Dashboard</button>

      <!-- Loading State -->
      <div class="loading-state" *ngIf="isLoading && !campaign">
        <div class="spinner-lg"></div>
        <p>Loading issue details...</p>
      </div>

      <!-- Error State -->
      <div class="error-state" *ngIf="errorMessage && !campaign">
        <div class="error-icon">❌</div>
        <h3>{{ errorMessage }}</h3>
        <button class="btn-secondary" (click)="goBack()">Back to Dashboard</button>
      </div>

      <!-- Campaign Detail -->
      <div class="detail-content" *ngIf="campaign">
        <!-- Header -->
        <div class="detail-header">
          <div class="header-meta">
            <span class="type-badge type-{{ campaign.issue_type }}">
              {{ getTypeIcon(campaign.issue_type) }} {{ campaign.issue_type | titlecase }}
            </span>
            <span class="status-badge status-{{ campaign.status }}">
              {{ getStatusLabel(campaign.status) }}
            </span>
            <span class="severity-badge sev-{{ campaign.severity }}">
              Severity {{ campaign.severity }}/5
            </span>
          </div>
          <h1 class="campaign-title">{{ campaign.title }}</h1>
          <p class="campaign-address">📍 {{ campaign.address }}</p>
          <div class="campaign-meta">
            <span>👥 {{ campaign.citizen_count }} citizen(s)</span>
            <span>📅 Reported {{ formatDate(campaign.created_at) }}</span>
            <span *ngIf="campaign.sla_deadline">
              <span [ngClass]="getSlaClass(campaign.sla_deadline)">
                ⏱️ SLA: {{ getSlaLabel(campaign.sla_deadline) }}
              </span>
            </span>
          </div>
        </div>

        <!-- Status Update Buttons -->
        <div class="status-actions" *ngIf="!isUpdating">
          <h3 class="section-title">Update Status</h3>
          <div class="action-buttons">
            <button
              class="btn-action btn-acknowledge"
              (click)="updateStatus('acknowledged')"
              [disabled]="isUpdating || campaign.status === 'acknowledged'"
            >
              ✅ Acknowledge
            </button>
            <button
              class="btn-action btn-progress"
              (click)="updateStatus('in_progress')"
              [disabled]="isUpdating || campaign.status === 'in_progress'"
            >
              🔨 In Progress
            </button>
            <button
              class="btn-action btn-resolve"
              (click)="confirmResolve()"
              [disabled]="isUpdating || campaign.status === 'verifying' || campaign.status === 'closed'"
            >
              ✔️ Resolved
            </button>
            <button
              class="btn-action btn-moreinfo"
              (click)="updateStatus('request_more_info')"
              [disabled]="isUpdating"
            >
              ❓ Request More Info
            </button>
          </div>
          <div class="alert alert-error" *ngIf="updateError">
            <span>⚠️</span>
            <p>{{ updateError }}</p>
          </div>
          <div class="alert alert-success" *ngIf="updateSuccess">
            <span>✅</span>
            <p>{{ updateSuccess }}</p>
          </div>
        </div>

        <!-- Updating State -->
        <div class="updating-state" *ngIf="isUpdating">
          <span class="spinner-sm"></span>
          <span>Updating status...</span>
        </div>

        <!-- Resolve Confirmation Dialog -->
        <div class="dialog-overlay" *ngIf="showResolveConfirm">
          <div class="dialog">
            <h3>Confirm Resolution</h3>
            <p>
              Are you sure this issue is fully resolved?
              <strong>This will trigger a 72-hour citizen verification window.</strong>
              Citizens will be asked to confirm the fix using photos.
            </p>
            <p class="dialog-warning">
              ⚠️ If verification fails (approval rate &lt; 60%), the issue will be reopened
              and your false-closure count will increase.
            </p>
            <div class="dialog-actions">
              <button class="btn-secondary" (click)="showResolveConfirm = false">Cancel</button>
              <button class="btn-resolve" (click)="updateStatus('resolved')">
                Yes, Mark Resolved
              </button>
            </div>
          </div>
        </div>

        <!-- Description -->
        <div class="section">
          <h3 class="section-title">Description</h3>
          <p class="description">{{ campaign.description }}</p>
        </div>

        <!-- Photos -->
        <div class="section" *ngIf="campaign.photos && campaign.photos.length > 0">
          <h3 class="section-title">Photos ({{ campaign.photos.length }})</h3>
          <div class="photo-grid">
            <div class="photo-card" *ngFor="let photo of campaign.photos">
              <div class="photo-placeholder">📷</div>
              <p class="photo-label">Uploaded {{ formatDate(photo.uploaded_at) }}</p>
            </div>
          </div>
          <p class="photo-note">Photos are stored securely. EXIF metadata has been stripped.</p>
        </div>

        <!-- Timeline -->
        <div class="section">
          <h3 class="section-title">Timeline</h3>
          <div class="timeline">
            <div
              class="timeline-item"
              *ngFor="let event of campaign.timeline; let last = last"
              [class.timeline-last]="last"
            >
              <div class="timeline-dot dot-{{ getTimelineColor(event.action) }}"></div>
              <div class="timeline-content">
                <div class="timeline-action">{{ getTimelineLabel(event.action) }}</div>
                <div class="timeline-notes" *ngIf="event.notes">{{ event.notes }}</div>
                <div class="timeline-meta">
                  <span class="timeline-actor">{{ formatActor(event.actor) }}</span>
                  <span class="timeline-time">{{ formatDate(event.timestamp) }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .detail-page {
      padding: 24px 32px;
      max-width: 900px;
      margin: 0 auto;
      color: white;
    }
    .btn-back {
      background: transparent; border: none; color: #888;
      cursor: pointer; font-size: 14px; padding: 0 0 20px 0;
      display: flex; align-items: center; gap: 6px;
    }
    .btn-back:hover { color: #e94560; }
    .loading-state, .error-state {
      display: flex; flex-direction: column; align-items: center;
      justify-content: center; padding: 80px; color: #888; text-align: center;
    }
    .error-icon { font-size: 48px; margin-bottom: 16px; }
    .error-state h3 { color: #ff8fa3; margin-bottom: 20px; }
    .detail-header {
      background: rgba(255,255,255,0.04);
      border: 1px solid rgba(255,255,255,0.08);
      border-radius: 12px;
      padding: 24px;
      margin-bottom: 24px;
    }
    .header-meta { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 14px; }
    .type-badge, .status-badge, .severity-badge {
      padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: 700;
      text-transform: capitalize; white-space: nowrap;
    }
    .type-pothole { background: rgba(244,67,54,0.2); color: #f44336; }
    .type-streetlight { background: rgba(255,193,7,0.2); color: #ffc107; }
    .type-water { background: rgba(33,150,243,0.2); color: #2196f3; }
    .type-garbage { background: rgba(76,175,80,0.2); color: #4caf50; }
    .type-sidewalk { background: rgba(255,152,0,0.2); color: #ff9800; }
    .type-other { background: rgba(158,158,158,0.2); color: #9e9e9e; }
    .status-open { background: rgba(158,158,158,0.2); color: #bdbdbd; }
    .status-acknowledged_pending { background: rgba(33,150,243,0.2); color: #64b5f6; }
    .status-acknowledged { background: rgba(33,150,243,0.25); color: #90caf9; }
    .status-in_progress { background: rgba(255,193,7,0.2); color: #ffd54f; }
    .status-resolved { background: rgba(76,175,80,0.2); color: #81c784; }
    .status-verifying { background: rgba(156,39,176,0.2); color: #ce93d8; }
    .status-closed { background: rgba(76,175,80,0.25); color: #a5d6a7; }
    .status-reopened { background: rgba(255,152,0,0.2); color: #ffcc80; }
    .status-escalated { background: rgba(244,67,54,0.25); color: #ef9a9a; }
    .sev-1, .sev-2 { background: rgba(76,175,80,0.2); color: #81c784; }
    .sev-3 { background: rgba(255,152,0,0.2); color: #ffb74d; }
    .sev-4, .sev-5 { background: rgba(244,67,54,0.2); color: #e57373; }
    .campaign-title { font-size: 22px; font-weight: 700; margin: 0 0 10px; color: white; }
    .campaign-address { color: #888; font-size: 14px; margin: 0 0 14px; }
    .campaign-meta { display: flex; gap: 20px; flex-wrap: wrap; font-size: 13px; color: #aaa; }
    .sla-ok { color: #81c784; font-weight: 600; }
    .sla-warning { color: #ffd54f; font-weight: 600; }
    .sla-critical { color: #ff7043; font-weight: 700; }
    .sla-overdue { color: #f44336; font-weight: 800; }
    .status-actions {
      background: rgba(255,255,255,0.03);
      border: 1px solid rgba(255,255,255,0.08);
      border-radius: 12px;
      padding: 20px 24px;
      margin-bottom: 24px;
    }
    .section-title { font-size: 14px; font-weight: 700; color: #888; text-transform: uppercase; letter-spacing: 1px; margin: 0 0 16px; }
    .action-buttons { display: flex; gap: 12px; flex-wrap: wrap; }
    .btn-action {
      padding: 10px 20px; border-radius: 8px; font-size: 13px; font-weight: 600;
      cursor: pointer; border: 1px solid; transition: all 0.2s;
    }
    .btn-action:disabled { opacity: 0.4; cursor: not-allowed; }
    .btn-acknowledge { border-color: #4caf50; color: #4caf50; background: rgba(76,175,80,0.1); }
    .btn-acknowledge:hover:not(:disabled) { background: rgba(76,175,80,0.25); }
    .btn-progress { border-color: #ffc107; color: #ffc107; background: rgba(255,193,7,0.1); }
    .btn-progress:hover:not(:disabled) { background: rgba(255,193,7,0.25); }
    .btn-resolve { border-color: #4caf50; color: white; background: #388e3c; padding: 10px 20px; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; }
    .btn-resolve:hover:not(:disabled) { background: #2e7d32; }
    .btn-resolve:disabled { opacity: 0.4; cursor: not-allowed; }
    .btn-moreinfo { border-color: #64b5f6; color: #64b5f6; background: rgba(33,150,243,0.1); }
    .btn-moreinfo:hover:not(:disabled) { background: rgba(33,150,243,0.25); }
    .btn-secondary {
      padding: 10px 20px; border-radius: 8px; font-size: 13px; font-weight: 600;
      cursor: pointer; border: 1px solid rgba(255,255,255,0.2); color: #ccc; background: transparent;
    }
    .btn-secondary:hover { background: rgba(255,255,255,0.08); }
    .alert { display: flex; gap: 10px; align-items: center; padding: 10px 14px; border-radius: 8px; margin-top: 12px; }
    .alert-error { background: rgba(233,69,96,0.12); border: 1px solid rgba(233,69,96,0.3); }
    .alert-success { background: rgba(76,175,80,0.12); border: 1px solid rgba(76,175,80,0.3); }
    .alert p { margin: 0; font-size: 13px; color: #ddd; }
    .updating-state { display: flex; align-items: center; gap: 10px; padding: 16px; color: #888; }
    .spinner-sm {
      width: 16px; height: 16px;
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
    .dialog-overlay {
      position: fixed; inset: 0;
      background: rgba(0,0,0,0.7);
      display: flex; align-items: center; justify-content: center;
      z-index: 1000;
    }
    .dialog {
      background: #1a1a2e;
      border: 1px solid rgba(255,255,255,0.15);
      border-radius: 16px;
      padding: 32px;
      max-width: 480px;
      width: 90%;
    }
    .dialog h3 { color: white; margin: 0 0 16px; font-size: 20px; }
    .dialog p { color: #ccc; font-size: 14px; line-height: 1.6; margin: 0 0 12px; }
    .dialog-warning { color: #ffb74d; background: rgba(255,152,0,0.1); border: 1px solid rgba(255,152,0,0.3); padding: 10px 12px; border-radius: 6px; }
    .dialog-actions { display: flex; gap: 12px; margin-top: 24px; justify-content: flex-end; }
    .section {
      background: rgba(255,255,255,0.03);
      border: 1px solid rgba(255,255,255,0.06);
      border-radius: 12px;
      padding: 20px 24px;
      margin-bottom: 20px;
    }
    .description { color: #ccc; font-size: 15px; line-height: 1.7; margin: 0; }
    .photo-grid { display: flex; gap: 12px; flex-wrap: wrap; }
    .photo-card {
      background: rgba(255,255,255,0.05);
      border: 1px solid rgba(255,255,255,0.1);
      border-radius: 8px;
      padding: 20px;
      text-align: center;
      min-width: 120px;
    }
    .photo-placeholder { font-size: 36px; }
    .photo-label { color: #777; font-size: 11px; margin: 8px 0 0; }
    .photo-note { color: #555; font-size: 11px; margin-top: 10px; }
    .timeline { position: relative; }
    .timeline-item {
      display: flex;
      gap: 16px;
      padding-bottom: 20px;
      position: relative;
    }
    .timeline-item::before {
      content: '';
      position: absolute;
      left: 9px;
      top: 20px;
      bottom: 0;
      width: 2px;
      background: rgba(255,255,255,0.08);
    }
    .timeline-last::before { display: none; }
    .timeline-dot {
      width: 20px; height: 20px; border-radius: 50%; flex-shrink: 0; margin-top: 2px;
    }
    .dot-blue { background: #1976d2; }
    .dot-yellow { background: #f57f17; }
    .dot-green { background: #2e7d32; }
    .dot-red { background: #c62828; }
    .dot-purple { background: #6a1b9a; }
    .dot-orange { background: #e65100; }
    .dot-gray { background: #555; }
    .timeline-content { flex: 1; }
    .timeline-action { font-weight: 600; color: white; font-size: 13px; text-transform: capitalize; }
    .timeline-notes { color: #aaa; font-size: 12px; margin-top: 2px; }
    .timeline-meta { display: flex; gap: 12px; margin-top: 4px; }
    .timeline-actor { color: #64b5f6; font-size: 11px; }
    .timeline-time { color: #555; font-size: 11px; }
  `]
})
export class IssueDetailComponent implements OnInit {
  campaign: CampaignDetail | null = null;
  isLoading = false;
  isUpdating = false;
  errorMessage = '';
  updateError = '';
  updateSuccess = '';
  showResolveConfirm = false;
  campaignId = '';

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private authService: AuthService,
    private apiService: ApiService
  ) {}

  ngOnInit(): void {
    this.campaignId = this.route.snapshot.paramMap.get('id') || '';
    if (this.campaignId) {
      this.loadCampaign();
    } else {
      this.errorMessage = 'Campaign not found.';
    }
  }

  loadCampaign(): void {
    this.isLoading = true;
    this.errorMessage = '';

    this.apiService.getCampaignDetail(this.campaignId).subscribe({
      next: (data) => {
        this.campaign = data;
        this.isLoading = false;
      },
      error: (err) => {
        this.isLoading = false;
        if (err.status === 401) {
          this.authService.logout();
        } else if (err.status === 403) {
          this.errorMessage = 'You do not have permission to view this issue.';
        } else if (err.status === 404) {
          this.errorMessage = 'Issue not found.';
        } else {
          this.errorMessage = 'Failed to load issue details. Please try again.';
        }
      }
    });
  }

  confirmResolve(): void {
    this.showResolveConfirm = true;
  }

  updateStatus(newStatus: string): void {
    const user = this.authService.currentOfficialUser;
    if (!user || !this.campaign) return;

    this.showResolveConfirm = false;
    this.isUpdating = true;
    this.updateError = '';
    this.updateSuccess = '';

    this.apiService.updateCampaignStatus(user.uid, {
      campaign_id: this.campaignId,
      status: newStatus,
    }).subscribe({
      next: (response) => {
        this.isUpdating = false;
        this.updateSuccess = `Status updated to "${response.new_status}" successfully.`;
        // Refresh campaign data
        setTimeout(() => {
          this.updateSuccess = '';
          this.loadCampaign();
        }, 2000);
      },
      error: (err) => {
        this.isUpdating = false;
        if (err.status === 401) {
          this.authService.logout();
        } else if (err.status === 403) {
          this.updateError = 'You are not authorized to update this campaign.';
        } else if (err.status === 422) {
          this.updateError = 'Invalid status value.';
        } else {
          this.updateError = 'Failed to update status. Please try again.';
        }
      }
    });
  }

  goBack(): void {
    this.router.navigate(['/dashboard']);
  }

  formatDate(dateStr: string): string {
    if (!dateStr) return '—';
    try {
      return new Date(dateStr).toLocaleString('en-IN', {
        day: '2-digit', month: 'short', year: 'numeric',
        hour: '2-digit', minute: '2-digit',
      });
    } catch {
      return dateStr;
    }
  }

  formatActor(actor: string): string {
    if (actor === 'system') return '🤖 System';
    return `👤 ${actor.slice(0, 8)}...`;
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
      open: 'Open', acknowledged_pending: 'Pending Acknowledgment',
      acknowledged: 'Acknowledged', in_progress: 'In Progress',
      resolved: 'Resolved', verifying: 'Verifying (72h window)',
      closed: 'Closed', reopened: 'Reopened', escalated: 'Escalated',
    };
    return labels[st] || st;
  }

  getSlaClass(sla: string | null): string {
    if (!sla) return '';
    const diffMs = new Date(sla).getTime() - Date.now();
    if (diffMs < 0) return 'sla-overdue';
    if (diffMs < 24 * 3600 * 1000) return 'sla-critical';
    if (diffMs < 48 * 3600 * 1000) return 'sla-warning';
    return 'sla-ok';
  }

  getSlaLabel(sla: string | null): string {
    if (!sla) return '—';
    const diffMs = new Date(sla).getTime() - Date.now();
    if (diffMs < 0) return '⚠️ OVERDUE';
    const days = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    const hours = Math.floor((diffMs % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
    return days > 0 ? `${days}d ${hours}h remaining` : `${hours}h remaining`;
  }

  getTimelineLabel(action: string): string {
    const labels: Record<string, string> = {
      created: 'Campaign Created', threshold_met: 'Threshold Met (3+ Citizens)',
      routing_drafted: 'Routing Draft Created', status_updated: 'Status Updated',
      escalated: 'Escalated', verified_and_closed: 'Verified & Closed',
      verification_failed: 'Verification Failed', citizen_joined: 'Citizen Joined',
      mass_issue_flagged: 'Flagged as Mass Issue',
    };
    return labels[action] || action.replace(/_/g, ' ');
  }

  getTimelineColor(action: string): string {
    const colors: Record<string, string> = {
      created: 'blue', threshold_met: 'blue', routing_drafted: 'blue',
      status_updated: 'yellow', in_progress: 'yellow',
      escalated: 'red', verification_failed: 'red',
      verified_and_closed: 'green', closed: 'green',
      citizen_joined: 'blue', mass_issue_flagged: 'orange',
    };
    return colors[action] || 'gray';
  }
}
