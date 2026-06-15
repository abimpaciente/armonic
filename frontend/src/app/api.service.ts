import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

export interface Hymn {
  hymn_id: string;
  title: string;
  key: string;
  mode: string;
  notes_per_voice: Record<string, number>;
  duration_seconds: number;
  tracks: string[];
}

export interface JobStatus {
  job_id: string;
  status: 'queued' | 'processing' | 'completed' | 'failed';
  progress: number;
  hymn_id?: string | null;
  error?: string | null;
}

@Injectable({ providedIn: 'root' })
export class ApiService {
  constructor(private http: HttpClient) {}

  upload(file: File): Observable<{ job_id: string; status: string }> {
    const fd = new FormData();
    fd.append('file', file);
    return this.http.post<{ job_id: string; status: string }>('/api/upload', fd);
  }

  job(id: string): Observable<JobStatus> {
    return this.http.get<JobStatus>(`/api/job/${id}`);
  }

  hymn(id: string): Observable<Hymn> {
    return this.http.get<Hymn>(`/api/hymn/${id}`);
  }

  hymns(): Observable<{ hymns: Hymn[] }> {
    return this.http.get<{ hymns: Hymn[] }>('/api/hymns');
  }

  midiUrl(hymnId: string, track: string): string {
    return `/api/hymn/${hymnId}/midi/${track}`;
  }
}
