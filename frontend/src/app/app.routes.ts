import { Routes } from '@angular/router';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { VoiceService } from './voice.service';

/** Si el usuario no eligió voz, lo manda al onboarding. */
const voiceGuard = () => {
  const vs = inject(VoiceService);
  const router = inject(Router);
  return vs.has() ? true : router.parseUrl('/onboarding');
};

export const routes: Routes = [
  { path: '', redirectTo: 'home', pathMatch: 'full' },
  {
    path: 'onboarding',
    loadComponent: () =>
      import('./pages/onboarding.component').then((m) => m.OnboardingComponent),
  },
  {
    path: 'home',
    canActivate: [voiceGuard],
    loadComponent: () =>
      import('./pages/home.component').then((m) => m.HomeComponent),
  },
  {
    path: 'hymn/:id',
    canActivate: [voiceGuard],
    loadComponent: () =>
      import('./pages/hymn.component').then((m) => m.HymnComponent),
  },
  { path: '**', redirectTo: 'home' },
];
