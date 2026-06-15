import { Component } from '@angular/core';
import { RouterLink, RouterOutlet } from '@angular/router';
import { VoiceService, VOICE_LABELS } from './voice.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, RouterLink],
  template: `
    <header>
      <a routerLink="/home" class="brand">🎵 armonic</a>
      @if (voiceLabel) {
        <a routerLink="/onboarding" class="myvoice">Mi voz: {{ voiceLabel }}</a>
      }
    </header>
    <main><router-outlet /></main>
  `,
  styles: [`
    header { display: flex; justify-content: space-between; align-items: center;
      padding: 14px 20px; background: var(--card); }
    .brand { font-weight: 700; font-size: 20px; color: var(--txt); text-decoration: none; }
    .myvoice { font-size: 13px; color: var(--accent); text-decoration: none; }
    main { max-width: 720px; margin: 0 auto; padding: 20px; }
  `],
})
export class AppComponent {
  voiceLabel = '';
  constructor(vs: VoiceService) {
    const v = vs.get();
    this.voiceLabel = v ? VOICE_LABELS[v] : '';
  }
}
