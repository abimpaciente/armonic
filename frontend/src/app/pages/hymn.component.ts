import { CommonModule } from '@angular/common';
import {
  Component,
  CUSTOM_ELEMENTS_SCHEMA,
  OnInit,
  signal,
} from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { ApiService, Hymn } from '../api.service';
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
        <h1>{{ h.title }}</h1>
        <p class="muted">{{ h.key }} · {{ h.mode }} ·
          {{ h.duration_seconds }}s · {{ h.tracks.length }} pistas</p>
        <div class="tempo">
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
            <a class="dl" [href]="api.midiUrl(h.hymn_id, v + '_solo', tempo())">⤓ solo</a>
            <a class="dl" [href]="api.midiUrl(h.hymn_id, v + '_realce', tempo())">⤓ con fondo</a>
          </div>
          <midi-player
            [attr.src]="api.midiUrl(h.hymn_id, v === myVoice ? v + '_realce' : v + '_solo', tempo())"
            sound-font></midi-player>
        </div>
      }

      <div class="card voice">
        <h3>Todas juntas</h3>
        <a class="dl" [href]="api.midiUrl(h.hymn_id, 'satb_completo', tempo())">⤓ descargar</a>
        <midi-player [attr.src]="api.midiUrl(h.hymn_id, 'satb_completo', tempo())" sound-font></midi-player>
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
    .tempo { margin-top: 12px; }
    .tempo label { display: block; font-size: 14px; margin-bottom: 4px; }
    .tempo input[type=range] { width: 100%; accent-color: var(--accent); }
    .tempo .hint { display: block; font-size: 12px; margin-top: 2px; }
  `],
})
export class HymnComponent implements OnInit {
  hymn = signal<Hymn | null>(null);
  tempo = signal(84);       // tempo aplicado (usado en las URLs de MIDI)
  tempoLabel = signal(84);  // tempo mostrado en vivo mientras se arrastra
  myVoice: Voice | null;
  labels = VOICE_LABELS;
  private order: Voice[] = ['soprano', 'alto', 'tenor', 'bass'];

  /** Aplica el nuevo tempo al soltar el slider (recarga los reproductores). */
  onTempo(e: Event): void {
    const bpm = +(e.target as HTMLInputElement).value;
    this.tempoLabel.set(bpm);
    this.tempo.set(bpm);
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
