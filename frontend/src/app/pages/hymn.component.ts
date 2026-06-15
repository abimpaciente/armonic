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
      </div>

      @for (v of orderedVoices(h); track v) {
        <div class="card voice" [class.mine]="v === myVoice">
          <h3>{{ labels[v] }}
            @if (v === myVoice) { <span class="badge">★ tu voz</span> }
          </h3>
          <div class="row">
            <a class="dl" [href]="api.midiUrl(h.hymn_id, v + '_solo')">⤓ solo</a>
            <a class="dl" [href]="api.midiUrl(h.hymn_id, v + '_realce')">⤓ con fondo</a>
          </div>
          <midi-player
            [attr.src]="api.midiUrl(h.hymn_id, v === myVoice ? v + '_realce' : v + '_solo')"
            sound-font></midi-player>
        </div>
      }

      <div class="card voice">
        <h3>Todas juntas</h3>
        <a class="dl" [href]="api.midiUrl(h.hymn_id, 'satb_completo')">⤓ descargar</a>
        <midi-player [attr.src]="api.midiUrl(h.hymn_id, 'satb_completo')" sound-font></midi-player>
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
  `],
})
export class HymnComponent implements OnInit {
  hymn = signal<Hymn | null>(null);
  myVoice: Voice | null;
  labels = VOICE_LABELS;
  private order: Voice[] = ['soprano', 'alto', 'tenor', 'bass'];

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
