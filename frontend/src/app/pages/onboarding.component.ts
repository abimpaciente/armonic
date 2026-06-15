import { Component } from '@angular/core';
import { Router } from '@angular/router';
import { Voice, VOICE_LABELS, VoiceService } from '../voice.service';

@Component({
  selector: 'app-onboarding',
  standalone: true,
  template: `
    <div class="card center">
      <h1>🎵 armonic</h1>
      <p class="muted">Antes de empezar, dinos qué voz cantas.<br />
        Destacaremos tu parte en cada himno.</p>
      <div class="voices-grid">
        @for (v of voices; track v) {
          <button class="voice-pick" (click)="choose(v)">{{ labels[v] }}</button>
        }
      </div>
    </div>
  `,
  styles: [`
    .center { text-align: center; max-width: 460px; margin: 40px auto; }
    h1 { font-size: 28px; margin-bottom: 4px; }
    .voices-grid { display: grid; gap: 12px; margin-top: 20px; }
    .voice-pick { padding: 16px; font-size: 16px; }
  `],
})
export class OnboardingComponent {
  voices: Voice[] = ['soprano', 'alto', 'tenor', 'bass'];
  labels = VOICE_LABELS;

  constructor(private vs: VoiceService, private router: Router) {}

  choose(v: Voice): void {
    this.vs.set(v);
    this.router.navigateByUrl('/home');
  }
}
