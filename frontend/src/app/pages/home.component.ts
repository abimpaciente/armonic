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
      <input class="title-in" placeholder="Título del himno (opcional)"
        [(ngModel)]="title" />
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
          <div class="hymn-row">
            <a class="t" [routerLink]="['/hymn', h.hymn_id]">► {{ h.title }}</a>
            <span class="muted meta">{{ h.key }} · {{ h.mode }}</span>
            <button class="del" title="Borrar este himno"
              (click)="remove(h)">🗑</button>
          </div>
        }
        <button class="clear" (click)="clearAll()">Vaciar biblioteca</button>
      } @else {
        <p class="muted">Aún no hay himnos. Sube el primero ↑</p>
      }
    </div>
  `,
  styles: [`
    .search { max-width: 200px; }
    .title-in { width: 100%; margin: 8px 0; }
    .hymn-row { display: flex; align-items: center; gap: 10px;
      padding: 12px; border-radius: 8px; }
    .hymn-row:hover { background: #1e293b; }
    .hymn-row .t { color: var(--accent); font-weight: 600; text-decoration: none;
      flex: 1; }
    .hymn-row .meta { white-space: nowrap; }
    .del { background: none; border: none; cursor: pointer; font-size: 16px;
      opacity: 0.6; padding: 2px 6px; }
    .del:hover { opacity: 1; }
    .clear { margin-top: 10px; background: none; border: 1px solid #475569;
      color: #94a3b8; border-radius: 8px; padding: 6px 12px; cursor: pointer; }
    .clear:hover { border-color: #f87171; color: #f87171; }
    .between { justify-content: space-between; align-items: center; }
    .error { color: #f87171; }
    progress { width: 100%; }
  `],
})
export class HomeComponent implements OnInit {
  file: File | null = null;
  title = '';
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
    this.api.upload(this.file, this.title).subscribe({
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

  remove(h: Hymn): void {
    if (!confirm(`¿Borrar "${h.title}"? Esto elimina sus pistas.`)) return;
    this.api.deleteHymn(h.hymn_id).subscribe({
      next: () => this.hymns.set(this.hymns().filter((x) => x.hymn_id !== h.hymn_id)),
      error: () => this.error.set('No se pudo borrar el himno'),
    });
  }

  clearAll(): void {
    if (!confirm('¿Borrar TODOS los himnos y sus pistas?')) return;
    this.api.clearLibrary().subscribe({
      next: () => this.hymns.set([]),
      error: () => this.error.set('No se pudo vaciar la biblioteca'),
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
