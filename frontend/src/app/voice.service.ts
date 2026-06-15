import { Injectable } from '@angular/core';

export type Voice = 'soprano' | 'alto' | 'tenor' | 'bass';

export const VOICE_LABELS: Record<Voice, string> = {
  soprano: 'Soprano',
  alto: 'Alto (contralto)',
  tenor: 'Tenor',
  bass: 'Bass (bajo)',
};

const KEY = 'armonic.voice';

/** Guarda la voz que canta el usuario (persistente en localStorage). */
@Injectable({ providedIn: 'root' })
export class VoiceService {
  get(): Voice | null {
    return (localStorage.getItem(KEY) as Voice) || null;
  }

  set(v: Voice): void {
    localStorage.setItem(KEY, v);
  }

  has(): boolean {
    return this.get() !== null;
  }
}
