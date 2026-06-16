import { CommonModule } from '@angular/common';
import {
  Component,
  CUSTOM_ELEMENTS_SCHEMA,
  OnInit,
  signal,
} from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { ApiService, Hymn, Timbre, VoiceVols } from '../api.service';
import { Voice, VOICE_LABELS, VoiceService } from '../voice.service';

interface KSyl { s: string; t: number; gi: number; }

@Component({
  selector: 'app-hymn',
  standalone: true,
  imports: [CommonModule, RouterLink],
  schemas: [CUSTOM_ELEMENTS_SCHEMA],
  template: `
    @if (hymn(); as h) {
      <a routerLink="/home" class="muted back">← Biblioteca</a>

      <div class="card head">
        <h1>{{ h.title }}
          <button class="icon" title="Renombrar" (click)="renameTitle(h)">✎</button>
        </h1>
        <div class="chips">
          <span class="chip">🎼 {{ h.key }}</span>
          <span class="chip">{{ h.mode === 'separado' ? 'SATB' : 'Armonizado' }}</span>
          <span class="chip">⏱ {{ h.duration_seconds }}s</span>
        </div>

        <div class="controls">
          <div class="control">
            <label>Sonido</label>
            <div class="seg">
              <button [class.active]="timbre() === 'voz'" (click)="setTimbre('voz')">🎤 Voz</button>
              <button [class.active]="timbre() === 'piano'" (click)="setTimbre('piano')">🎹 Piano</button>
            </div>
          </div>
          <div class="control grow">
            <label>Tempo · <strong>{{ tempoLabel() }} BPM</strong></label>
            <input type="range" min="50" max="140" step="2"
              [value]="tempo()"
              (input)="tempoLabel.set(+$any($event.target).value)"
              (change)="onTempo($event)">
          </div>
        </div>
      </div>

      @if (h.lyrics?.verses?.length) {
        <div class="card lyrics">
          <h3>Letra <span class="muted">· OCR</span>
            @if (!editing()) {
              <button class="icon" title="Editar letra" (click)="startEdit(h)">✎</button>
            }
          </h3>

          @if (editing()) {
            @for (v of editVerses; track $index) {
              <textarea rows="2" [value]="v"
                (input)="editVerses[$index] = $any($event.target).value"></textarea>
            }
            <div class="row">
              <button (click)="saveEdit(h)">Guardar</button>
              <button class="ghost" (click)="editing.set(false)">Cancelar</button>
            </div>
          } @else {
            <midi-player
              [attr.src]="api.midiUrl(h.hymn_id, 'satb_completo', tempo(), timbre())"
              sound-font (start)="onSingStart($event)" (stop)="onSingStop()"></midi-player>
            <p class="verse lead karaoke">
              @for (word of kWords(); track $index) {<span class="kw">@for (syl of word; track syl.gi) {<span class="syl" [id]="'syl-' + syl.gi" [class.on]="syl.gi === activeSyl()">{{ syl.s }}</span>}</span> }
            </p>
            @for (v of otherVerses(h); track $index) {
              <p class="verse muted">{{ v }}</p>
            }
          }
        </div>
      }

      <div class="voices">
        @for (v of orderedVoices(h); track v) {
          <div class="card voice" [class.mine]="v === myVoice">
            <h3>{{ labels[v] }}
              @if (v === myVoice) { <span class="badge">★ tu voz</span> }
            </h3>
            <div class="row links">
              <a class="dl" [href]="api.midiUrl(h.hymn_id, v + '_solo', tempo(), timbre())">⤓ solo</a>
              <a class="dl" [href]="api.midiUrl(h.hymn_id, v + '_realce', tempo(), timbre())">⤓ con fondo</a>
            </div>
            <midi-player
              [attr.src]="api.midiUrl(h.hymn_id, v === myVoice ? v + '_realce' : v + '_solo', tempo(), timbre())"
              sound-font></midi-player>
          </div>
        }
      </div>

      <div class="card voice">
        <h3>Mezclador SATB <span class="muted">· volumen por voz</span></h3>
        <div class="mixer">
          @for (v of order; track v) {
            <div class="vrow">
              <span class="vlabel">{{ labels[v] }}</span>
              <input type="range" min="0" max="127" [value]="vols()[v]"
                (change)="setVol(v, $event)">
            </div>
          }
        </div>
        <midi-player [attr.src]="api.mixUrl(h.hymn_id, vols(), tempo(), timbre())" sound-font></midi-player>
      </div>

      @if (h.image_ext) {
        <details class="card sheet">
          <summary>Ver partitura original</summary>
          <img [src]="api.imageUrl(h.hymn_id)" alt="Partitura original" />
        </details>
      }
    } @else {
      <p class="muted">Cargando…</p>
    }
  `,
  styles: [`
    .back { display: inline-block; margin-bottom: 12px; text-decoration: none; }
    .head h1 { display: flex; align-items: center; gap: 8px; font-size: 26px; }
    .icon { background: none; box-shadow: none; color: var(--muted); font-size: 15px; padding: 2px 6px; }
    .icon:hover { color: var(--accent); }
    .ghost { background: transparent; color: var(--muted); border: 1px solid var(--line); }

    .controls { display: flex; gap: 18px; flex-wrap: wrap; margin-top: 16px; }
    .control label { display: block; font-size: 13px; color: var(--muted); margin-bottom: 6px; }
    .control.grow { flex: 1; min-width: 200px; }
    .control input[type=range] { width: 100%; accent-color: var(--accent); }

    .lyrics h3 { display: flex; align-items: center; gap: 6px; }
    .lyrics textarea { width: 100%; margin-bottom: 8px; padding: 8px; border-radius: 8px;
      background: var(--bg2); color: var(--txt); border: 1px solid var(--line); resize: vertical;
      font: inherit; }
    .lyrics .verse { font-size: 17px; line-height: 2; margin: 6px 0; }
    .lyrics .lead { color: var(--txt); font-weight: 500; }
    .lyrics .kw { display: inline-block; }
    .lyrics .syl { padding: 1px 1px; border-radius: 5px; transition: background 0.1s; }
    .lyrics .syl.on { background: var(--accent); color: #042233; }
    .lyrics midi-player { margin: 8px 0 14px; }

    .voices { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; }
    .voices .card { margin-bottom: 0; }
    .voice.mine { border-color: var(--accent); box-shadow: 0 0 0 1px var(--accent), 0 8px 24px rgba(0,0,0,0.25); }
    .voice h3 { margin: 0 0 10px; }
    .badge { font-size: 11px; color: var(--accent); margin-left: 6px; }
    .links { margin-bottom: 8px; }
    .dl { color: var(--accent); text-decoration: none; margin-right: 14px; font-size: 13px; }
    midi-player { margin-top: 8px; }

    .mixer { display: grid; gap: 8px; margin-bottom: 8px; }
    .vrow { display: flex; align-items: center; gap: 12px; }
    .vlabel { width: 120px; font-size: 13px; color: var(--muted); }
    .vrow input[type=range] { flex: 1; accent-color: var(--accent); }

    .sheet summary { cursor: pointer; font-weight: 600; }
    .sheet img { width: 100%; border-radius: 10px; margin-top: 12px; background: #fff; }
  `],
})
export class HymnComponent implements OnInit {
  hymn = signal<Hymn | null>(null);
  tempo = signal(84);
  tempoLabel = signal(84);
  timbre = signal<Timbre>((localStorage.getItem('armonic.timbre') as Timbre) || 'voz');
  vols = signal<VoiceVols>({ soprano: 90, alto: 90, tenor: 90, bass: 90 });
  activeSyl = signal(-1);
  kWords = signal<KSyl[][]>([]);
  editing = signal(false);
  editVerses: string[] = [];
  myVoice: Voice | null;
  labels = VOICE_LABELS;
  order: Voice[] = ['soprano', 'alto', 'tenor', 'bass'];
  private flat: KSyl[] = [];
  private singing = false;
  private lastSyl = -1;

  constructor(
    public api: ApiService,
    private route: ActivatedRoute,
    private vs: VoiceService,
  ) {
    this.myVoice = this.vs.get();
  }

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id')!;
    this.api.hymn(id).subscribe((h) => { this.hymn.set(h); this.buildKaraoke(h); });
  }

  private buildKaraoke(h: Hymn): void {
    const words: KSyl[][] = [];
    const flat: KSyl[] = [];
    let gi = 0;
    for (const word of h.lyrics?.karaoke ?? []) {
      const syls = word.syllables.map((s) => {
        const k: KSyl = { s: s.s, t: s.t, gi: gi++ };
        flat.push(k);
        return k;
      });
      words.push(syls);
    }
    this.kWords.set(words);
    this.flat = flat;
  }

  onTempo(e: Event): void {
    const bpm = +(e.target as HTMLInputElement).value;
    this.tempoLabel.set(bpm);
    this.tempo.set(bpm);
  }

  setTimbre(t: Timbre): void {
    this.timbre.set(t);
    localStorage.setItem('armonic.timbre', t);
  }

  setVol(v: Voice, e: Event): void {
    this.vols.set({ ...this.vols(), [v]: +(e.target as HTMLInputElement).value });
  }

  renameTitle(h: Hymn): void {
    const value = prompt('Título del himno:', h.title);
    const title = value?.trim();
    if (!title || title === h.title) return;
    this.api.rename(h.hymn_id, title).subscribe({ next: () => this.hymn.set({ ...h, title }) });
  }

  startEdit(h: Hymn): void {
    this.editVerses = [...(h.lyrics?.verses ?? [])];
    this.editing.set(true);
  }

  saveEdit(h: Hymn): void {
    this.api.updateLyrics(h.hymn_id, this.editVerses).subscribe({
      next: (r) => {
        const updated = { ...h, lyrics: r.lyrics };
        this.hymn.set(updated);
        this.buildKaraoke(updated);
        this.editing.set(false);
      },
    });
  }

  /** Resalta la sílaba de la estrofa 1 según el tiempo del reproductor. */
  onSingStart(ev: Event): void {
    const player = ev.target as unknown as { currentTime: number };
    this.singing = true;
    const tick = () => {
      if (!this.singing) return;
      const ql = (player.currentTime || 0) * this.tempo() / 60;
      let idx = -1;
      for (let i = 0; i < this.flat.length; i++) {
        if (this.flat[i].t <= ql + 0.05) idx = this.flat[i].gi; else break;
      }
      if (idx !== this.lastSyl) {
        this.lastSyl = idx;
        this.activeSyl.set(idx);
        const el = idx >= 0 ? document.getElementById('syl-' + idx) : null;
        el?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
      }
      requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }

  onSingStop(): void {
    this.singing = false;
    this.lastSyl = -1;
    this.activeSyl.set(-1);
  }

  otherVerses(h: Hymn): string[] {
    return (h.lyrics?.verses ?? []).slice(1);
  }

  orderedVoices(h: Hymn): Voice[] {
    const available = this.order.filter((v) => h.tracks.includes(v + '_solo'));
    if (!this.myVoice) return available;
    return [
      ...available.filter((v) => v === this.myVoice),
      ...available.filter((v) => v !== this.myVoice),
    ];
  }
}
