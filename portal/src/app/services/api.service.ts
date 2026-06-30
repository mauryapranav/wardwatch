/**
 * WardWatch - API Service (Angular)
 *
 * All HTTP calls to the FastAPI backend go through this service.
 * The Authorization header is attached by AuthInterceptor.
 */
import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface OfficialIssue {
  campaign_id: string;
  title: string;
  issue_type: string;
  severity: number;
  citizen_count: number;
  status: string;
  sla_deadline: string | null;
  created_at: string;
  address: string;
}

export interface CampaignDetail {
  campaign_id: string;
  title: string;
  description: string;
  issue_type: string;
  severity: number;
  location: { lat: number; lng: number };
  address: string;
  ward_id: string;
  status: string;
  founder_id: string;
  citizen_count: number;
  sla_deadline: string | null;
  created_at: string;
  timeline: TimelineEvent[];
  photos: Photo[];
  members_count: number;
}

export interface TimelineEvent {
  action: string;
  actor: string;
  timestamp: string;
  notes: string;
}

export interface Photo {
  photo_id: string;
  storage_path: string;
  thumbnail_url: string;
  uploaded_at: string;
}

export interface StatusUpdateRequest {
  campaign_id: string;
  status: string;
  notes?: string;
}

export interface StatusUpdateResponse {
  campaign_id: string;
  old_status: string;
  new_status: string;
  updated_at: string;
}

@Injectable({ providedIn: 'root' })
export class ApiService {
  private readonly baseUrl = environment.apiBaseUrl;

  constructor(private http: HttpClient) {}

  /**
   * GET /api/v1/officials/{official_id}/issues
   */
  getOfficialIssues(officialId: string): Observable<OfficialIssue[]> {
    return this.http.get<OfficialIssue[]>(
      `${this.baseUrl}/api/v1/officials/${officialId}/issues`
    );
  }

  /**
   * GET /api/v1/issues/{campaign_id}
   */
  getCampaignDetail(campaignId: string): Observable<CampaignDetail> {
    return this.http.get<CampaignDetail>(
      `${this.baseUrl}/api/v1/issues/${campaignId}`
    );
  }

  /**
   * PUT /api/v1/officials/{official_id}/status
   */
  updateCampaignStatus(
    officialId: string,
    request: StatusUpdateRequest
  ): Observable<StatusUpdateResponse> {
    return this.http.put<StatusUpdateResponse>(
      `${this.baseUrl}/api/v1/officials/${officialId}/status`,
      request
    );
  }
}
