import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

export interface Syllable { s: string; t: number; }
export interface KaraokeWord { syllables: Syllable[]; }
export interface Lyrics { verses: string[]; karaoke: KaraokeWord[]; }
export interface VoiceVols { soprano: number; alto: number; tenor: number; bass: number; }

export interface Hymn {
  hymn_id: string;
  title: string;
  key: string;
  mode: string;
  notes_per_voice: Record<string, number>;
  duration_seconds: number;
  tracks: string[];
  image_ext?: string | null;
  lyrics?: Lyrics | null;
}

export type Timbre = 'voz' | 'piano';

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

  upload(file: File, title = ''): Observable<{ job_id: string; status: string }> {
    const fd = new FormData();
    fd.append('file', file);
    if (title.trim()) fd.append('title', title.trim());
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

  deleteHymn(id: string): Observable<{ deleted: string }> {
    return this.http.delete<{ deleted: string }>(`/api/hymn/${id}`);
  }

  rename(id: string, title: string): Observable<{ hymn_id: string; title: string }> {
    return this.http.patch<{ hymn_id: string; title: string }>(`/api/hymn/${id}`, { title });
  }

  updateLyrics(id: string, verses: string[]): Observable<{ lyrics: Lyrics | null }> {
    return this.http.patch<{ lyrics: Lyrics | null }>(`/api/hymn/${id}/lyrics`, { verses });
  }

  imageUrl(id: string): string {
    return `/api/hymn/${id}/image`;
  }

  mixUrl(id: string, v: VoiceVols, tempo?: number, timbre?: Timbre): string {
    const p = new URLSearchParams();
    p.set('soprano', '' + v.soprano);
    p.set('alto', '' + v.alto);
    p.set('tenor', '' + v.tenor);
    p.set('bass', '' + v.bass);
    if (tempo) p.set('tempo', '' + tempo);
    if (timbre && timbre !== 'voz') p.set('timbre', timbre);
    return `/api/hymn/${id}/mix?${p.toString()}`;
  }

  clearLibrary(): Observable<{ deleted: number }> {
    return this.http.delete<{ deleted: number }>('/api/hymns');
  }

  midiUrl(hymnId: string, track: string, tempo?: number, timbre?: Timbre): string {
    const params = new URLSearchParams();
    if (tempo) params.set('tempo', String(tempo));
    if (timbre && timbre !== 'voz') params.set('timbre', timbre);
    const qs = params.toString();
    return `/api/hymn/${hymnId}/midi/${track}${qs ? '?' + qs : ''}`;
  }
}
