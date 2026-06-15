import { CommonModule } from '@angular/common';
import { Component, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { ApiService, Hymn } from '../api.service';

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <div class="card">
      <h2>Subir un himno</h2>
      <p class="muted">Sube una foto del himnario (JPG/PNG) o un archivo
        MusicXML/MIDI.</p>
      <div class="row">
        <input type="file" (change)="pick($event)"
          accept=".jpg,.jpeg,.png,.mxl,.musicxml,.xml,.mid,.midi" />
        <button (click)="upload()" [disabled]="!file || busy()">Procesar</button>
      </div>
      @if (status()) { <p class="status">{{ status() }}</p> }
      @if (busy()) { <progress [value]="progress()" max="100"></progress> }
      @if (error()) { <p class="error">⚠ {{ error() }}</p> }
    </div>

    <div class="card">
      <div class="row between">
        <h2>Biblioteca</h2>
        <input class="search" placeholder="Buscar título…"
          [(ngModel)]="query" />
      </div>
      @if (filtered().length) {
        @for (h of filtered(); track h.hymn_id) {
          <a class="hymn-row" [routerLink]="['/hymn', h.hymn_id]">
            <span class="t">► {{ h.title }}</span>
            <span class="muted">{{ h.key }} · {{ h.mode }}</span>
          </a>
        }
      } @else {
        <p class="muted">Aún no hay himnos. Sube el primero ↑</p>
      }
    </div>
  `,
  styles: [`
    .search { max-width: 200px; }
    .hymn-row { display: flex; justify-content: space-between; align-items: center;
      padding: 12px; border-radius: 8px; text-decoration: none; color: inherit; }
    .hymn-row:hover { background: #1e293b; }
    .hymn-row .t { color: var(--accent); font-weight: 600; }
    .between { justify-content: space-between; align-items: center; }
    .error { color: #f87171; }
    progress { width: 100%; }
  `],
})
export class HomeComponent implements OnInit {
  file: File | null = null;
  query = '';
  hymns = signal<Hymn[]>([]);
  status = signal('');
  error = signal('');
  busy = signal(false);
  progress = signal(0);

  constructor(private api: ApiService, private router: Router) {}

  ngOnInit(): void {
    this.loadLibrary();
  }

  filtered(): Hymn[] {
    const q = this.query.toLowerCase().trim();
    return this.hymns().filter((h) => !q || h.title.toLowerCase().includes(q));
  }

  pick(e: Event): void {
    this.file = (e.target as HTMLInputElement).files?.[0] ?? null;
    this.error.set('');
  }

  upload(): void {
    if (!this.file) return;
    this.busy.set(true);
    this.error.set('');
    this.status.set('Subiendo…');
    this.progress.set(10);
    this.api.upload(this.file).subscribe({
      next: (r) => this.poll(r.job_id),
      error: (e) => this.fail(e?.error?.detail || 'No se pudo subir'),
    });
  }

  private poll(jobId: string): void {
    this.api.job(jobId).subscribe({
      next: (j) => {
        this.progress.set(j.progress || 0);
        if (j.status === 'processing') this.status.set('Procesando partitura…');
        if (j.status === 'completed' && j.hymn_id) {
          this.status.set('✓ Listo');
          this.busy.set(false);
          this.router.navigate(['/hymn', j.hymn_id]);
          return;
        }
        if (j.status === 'failed') {
          this.fail(j.error || 'Falló el procesamiento');
          return;
        }
        setTimeout(() => this.poll(jobId), 1500);
      },
      error: () => this.fail('Error consultando el estado'),
    });
  }

  private fail(msg: string): void {
    this.busy.set(false);
    this.status.set('');
    this.error.set(msg);
  }

  private loadLibrary(): void {
    this.api.hymns().subscribe((r) => this.hymns.set(r.hymns));
  }
}
