import { provideHttpClient } from '@angular/common/http';
import { ApplicationConfig, importProvidersFrom } from '@angular/core';
import { NgxChessBoardModule } from 'ngx-chess-board';

export const appConfig: ApplicationConfig = {
  providers: [
    provideHttpClient(),
    importProvidersFrom(NgxChessBoardModule.forRoot())
  ]
};
