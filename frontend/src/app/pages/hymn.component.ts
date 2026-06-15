import { CommonModule } from '@angular/common';
import {
  Component,
  CUSTOM_ELEMENTS_SCHEMA,
  OnInit,
  signal,
} from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { ApiService, Hymn, Timbre } from '../api.service';
import { Voice, VOICE_LABELS, VoiceService } from '../voice.service';

@Component({
  selector: 'app-hymn',
  standalone: true,
  imports: [CommonModule, RouterLink],
  schemas: [CUSTOM_ELEMENTS_SCHEMA], // permite <midi-player> (web component)
  template: `
    @if (hymn(); as h) {
      <a routerLink="/home" class="muted back">← Biblioteca</a>
      <div class="card">
        <h1>{{ h.title }}
          <button class="edit" title="Renombrar" (click)="renameTitle(h)">✎</button>
        </h1>
        <p class="muted">{{ h.key }} · {{ h.mode }} ·
          {{ h.duration_seconds }}s · {{ h.tracks.length }} pistas</p>

        @if (h.image_ext) {
          <div class="sheet">
            <img [src]="api.imageUrl(h.hymn_id)" alt="Partitura original" />
            <span class="muted hint">Partitura original (letra y notas).</span>
          </div>
        }

        <div class="control">
          <label>Sonido:</label>
          <div class="seg">
            <button [class.active]="timbre() === 'voz'" (click)="setTimbre('voz')">🎤 Voz (coro)</button>
            <button [class.active]="timbre() === 'piano'" (click)="setTimbre('piano')">🎹 Piano</button>
          </div>
        </div>

        <div class="tempo control">
          <label>Tempo de ensayo: <strong>{{ tempoLabel() }} BPM</strong></label>
          <input type="range" min="50" max="140" step="2"
            [value]="tempo()"
            (input)="tempoLabel.set(+$any($event.target).value)"
            (change)="onTempo($event)">
          <span class="muted hint">Suelta el control para aplicar el nuevo tempo.</span>
        </div>
      </div>

      @for (v of orderedVoices(h); track v) {
        <div class="card voice" [class.mine]="v === myVoice">
          <h3>{{ labels[v] }}
            @if (v === myVoice) { <span class="badge">★ tu voz</span> }
          </h3>
          <div class="row">
            <a class="dl" [href]="api.midiUrl(h.hymn_id, v + '_solo', tempo(), timbre())">⤓ solo</a>
            <a class="dl" [href]="api.midiUrl(h.hymn_id, v + '_realce', tempo(), timbre())">⤓ con fondo</a>
          </div>
          <midi-player
            [attr.src]="api.midiUrl(h.hymn_id, v === myVoice ? v + '_realce' : v + '_solo', tempo(), timbre())"
            sound-font></midi-player>
        </div>
      }

      <div class="card voice">
        <h3>Todas juntas</h3>
        <a class="dl" [href]="api.midiUrl(h.hymn_id, 'satb_completo', tempo(), timbre())">⤓ descargar</a>
        <midi-player [attr.src]="api.midiUrl(h.hymn_id, 'satb_completo', tempo(), timbre())" sound-font></midi-player>
      </div>
    } @else {
      <p class="muted">Cargando…</p>
    }
  `,
  styles: [`
    .back { display: inline-block; margin-bottom: 10px; text-decoration: none; }
    .voice.mine { border: 1px solid var(--accent); box-shadow: 0 0 0 1px var(--accent); }
    .voice h3 { margin: 0 0 8px; }
    .badge { font-size: 11px; color: var(--accent); margin-left: 6px; }
    .dl { color: var(--accent); text-decoration: none; margin-right: 14px; font-size: 14px; }
    midi-player { width: 100%; margin-top: 8px; }
    h1 { display: flex; align-items: center; gap: 8px; }
    .edit { background: none; border: none; cursor: pointer; font-size: 16px;
      opacity: 0.5; padding: 0; }
    .edit:hover { opacity: 1; }
    .sheet { margin: 12px 0; }
    .sheet img { width: 100%; border-radius: 8px; border: 1px solid #334155;
      background: #fff; }
    .control { margin-top: 12px; }
    .control label { display: block; font-size: 14px; margin-bottom: 6px; }
    .control input[type=range] { width: 100%; accent-color: var(--accent); }
    .hint { display: block; font-size: 12px; margin-top: 2px; }
    .seg { display: inline-flex; border: 1px solid #475569; border-radius: 8px;
      overflow: hidden; }
    .seg button { background: #1e293b; color: #cbd5e1; border: none;
      padding: 8px 14px; cursor: pointer; font-size: 14px; }
    .seg button.active { background: var(--accent); color: #0f172a; font-weight: 600; }
  `],
})
export class HymnComponent implements OnInit {
  hymn = signal<Hymn | null>(null);
  tempo = signal(84);       // tempo aplicado (usado en las URLs de MIDI)
  tempoLabel = signal(84);  // tempo mostrado en vivo mientras se arrastra
  timbre = signal<Timbre>(
    (localStorage.getItem('armonic.timbre') as Timbre) || 'voz',
  );
  myVoice: Voice | null;
  labels = VOICE_LABELS;
  private order: Voice[] = ['soprano', 'alto', 'tenor', 'bass'];

  /** Aplica el nuevo tempo al soltar el slider (recarga los reproductores). */
  onTempo(e: Event): void {
    const bpm = +(e.target as HTMLInputElement).value;
    this.tempoLabel.set(bpm);
    this.tempo.set(bpm);
  }

  /** Cambia el timbre (voz coral o piano) y recuerda la preferencia. */
  setTimbre(t: Timbre): void {
    this.timbre.set(t);
    localStorage.setItem('armonic.timbre', t);
  }

  /** Renombra el himno (útil cuando el OCR no detectó título). */
  renameTitle(h: Hymn): void {
    const value = prompt('Título del himno:', h.title);
    const title = value?.trim();
    if (!title || title === h.title) return;
    this.api.rename(h.hymn_id, title).subscribe({
      next: () => this.hymn.set({ ...h, title }),
    });
  }

  constructor(
    public api: ApiService,
    private route: ActivatedRoute,
    private vs: VoiceService,
  ) {
    this.myVoice = this.vs.get();
  }

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id')!;
    this.api.hymn(id).subscribe((h) => this.hymn.set(h));
  }

  /** Tu voz primero, luego el resto en orden SATB. */
  orderedVoices(h: Hymn): Voice[] {
    const available = this.order.filter((v) => h.tracks.includes(v + '_solo'));
    if (!this.myVoice) return available;
    return [
      ...available.filter((v) => v === this.myVoice),
      ...available.filter((v) => v !== this.myVoice),
    ];
  }
}
