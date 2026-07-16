import { CommonModule } from '@angular/common';
import { Component, ViewChild } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { NgxChessBoardModule, NgxChessBoardView } from 'ngx-chess-board';
import {
  AgentSnapshot,
  ChessAgentService,
  CoachResponse,
  EvaluationResponse,
  MoveResponse,
  TheoryMove,
  VectorSearchResult,
  VideoResult
} from './chess-agent.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, FormsModule, NgxChessBoardModule],
  templateUrl: './app.component.html',
  styleUrl: './app.component.css'
})
export class AppComponent {
  @ViewChild('board') board?: NgxChessBoardView;

  openingQuery = 'Defense sicilienne';
  currentFen = 'Position initiale';
  loadingPosition = false;
  loadingResources = false;
  loadingCoach = false;
  positionError = '';
  resourceError = '';
  coachError = '';
  moveResponse?: MoveResponse;
  evaluation?: EvaluationResponse;
  coachResponse?: CoachResponse;
  contextResults: VectorSearchResult[] = [];
  videos: VideoResult[] = [];

  constructor(private readonly agent: ChessAgentService) {}

  onMoveChange(): void {
    this.refreshFen();
    this.analyzeCurrentPosition();
  }

  analyzeCurrentPosition(): void {
    const fen = this.readFen();
    if (!fen) {
      return;
    }

    this.loadingPosition = true;
    this.positionError = '';
    this.agent.analyzePosition(fen).subscribe({
      next: (snapshot: AgentSnapshot) => {
        this.moveResponse = snapshot.moves;
        this.evaluation = snapshot.evaluation;
        this.currentFen = snapshot.evaluation.fen;
        this.loadingPosition = false;
      },
      error: (error) => {
        this.positionError = error?.error?.detail ?? 'Analyse indisponible';
        this.loadingPosition = false;
      }
    });
  }

  loadResources(): void {
    const query = this.openingQuery.trim();
    if (!query) {
      return;
    }

    this.loadingResources = true;
    this.resourceError = '';
    this.agent.searchOpening(query).subscribe({
      next: (response) => {
        this.contextResults = response.results;
        this.loadVideos(query);
      },
      error: (error) => {
        this.contextResults = [];
        this.resourceError = error?.error?.detail ?? 'Contexte indisponible';
        this.loadVideos(query);
      }
    });
  }

  askCoach(): void {
    const fen = this.readFen();
    if (!fen) {
      return;
    }

    this.loadingCoach = true;
    this.coachError = '';
    this.agent.coachPosition(fen, this.openingQuery).subscribe({
      next: (response) => {
        this.coachResponse = response;
        this.moveResponse = { fen: response.fen, moves: response.theory_moves };
        if (response.evaluation) {
          this.evaluation = response.evaluation;
          this.currentFen = response.evaluation.fen;
        } else {
          this.currentFen = response.fen;
        }
        this.contextResults = response.context;
        this.videos = response.videos;
        this.loadingCoach = false;
      },
      error: (error) => {
        this.coachError = error?.error?.detail ?? 'Conseil agent indisponible';
        this.loadingCoach = false;
      }
    });
  }

  resetBoard(): void {
    this.board?.reset();
    this.refreshFen();
    this.moveResponse = undefined;
    this.evaluation = undefined;
    this.positionError = '';
    this.coachError = '';
    this.coachResponse = undefined;
  }

  reverseBoard(): void {
    this.board?.reverse();
  }

  trackMove(_: number, move: TheoryMove): string {
    return move.uci;
  }

  trackContext(_: number, result: VectorSearchResult): string {
    return `${result.opening}-${result.eco}`;
  }

  trackVideo(_: number, video: VideoResult): string {
    return video.video_id;
  }

  trackTool(_: number, tool: string): string {
    return tool;
  }

  trackWarning(index: number): number {
    return index;
  }

  private loadVideos(opening: string): void {
    this.agent.searchVideos(opening).subscribe({
      next: (response) => {
        this.videos = response.videos;
        this.loadingResources = false;
      },
      error: (error) => {
        this.videos = [];
        this.resourceError = this.resourceError || error?.error?.detail || 'Videos indisponibles';
        this.loadingResources = false;
      }
    });
  }

  private readFen(): string {
    return this.board?.getFEN() ?? '';
  }

  private refreshFen(): void {
    this.currentFen = this.readFen() || 'Position initiale';
  }
}
