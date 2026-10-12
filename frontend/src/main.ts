import { bootstrapApplication } from '@angular/platform-browser';
import { provideHttpClient } from '@angular/common/http';
import { Component, Injectable, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';

type Ticket = { id: string; code: string; name: string; card: string | null; service: string; status: string; desk: number | null };
type State = { desks: { number: number; ticket: Ticket | null }[]; waiting: Ticket[]; total_today: number; waiting_count: number; service_seconds: number };

@Injectable({ providedIn: 'root' })
class QueueApi {
  private http = inject(HttpClient);
  state() { return this.http.get<State>('/api/state'); }
  create() { return this.http.post<Ticket>('/api/tickets', {}); }
}

@Component({
  selector: 'app-root', standalone: true, imports: [CommonModule],
  template: `
  <div class="app-shell">
    <aside class="sidebar">
      <div class="brand"><div class="brand-mark">✳</div><div><strong>vitalia</strong><small>LABORATORIO CLÍNICO</small></div></div>
      <div class="side-label">CENTRO DE ATENCIÓN</div>
      <button class="nav" [class.active]="section === 'turnos'" (click)="goTo('turnos')"><span>▦</span> Turnos</button>
      <button class="nav" [class.active]="section === 'atencion'" (click)="goTo('atencion')"><span>♧</span> Atención</button>
      <div class="side-bottom"><div class="side-help">¿Necesitas ayuda?<br><b>Estamos para ti.</b></div><div class="profile"><div class="avatar">VC</div><div><b>Centro Vitalia</b><small>Sucursal Centro</small></div><span class="dots">···</span></div></div>
    </aside>
    <main class="main">
      <header class="topbar"><div class="crumb">Atención <span>/</span> <b>Gestión de turnos</b></div><div class="top-right"><span class="open-dot"></span> Sucursal abierta <span class="divider"></span><span class="user-avatar">VC</span></div></header>
      <div class="content">
        <div class="page-title" id="turnos"><div><div class="eyebrow">LABORATORIO · SUCURSAL CENTRO</div><h1>Gestión de turnos</h1><p>Una atención clara y cercana, desde que llegas hasta que te vas.</p></div><div class="date-pill"><span>◷</span> {{ today }}</div></div>
        <section class="metrics"><div class="metric"><div class="metric-icon mint">▤</div><div><small>Turnos de hoy</small><strong>{{ state?.total_today ?? '—' }}</strong></div><span class="metric-note">todos</span></div><div class="metric"><div class="metric-icon amber">◷</div><div><small>En espera</small><strong>{{ state?.waiting_count ?? '—' }}</strong></div><span class="metric-note">en fila</span></div><div class="metric"><div class="metric-icon blue">▦</div><div><small>Mesas activas</small><strong>{{ occupied }}<em> / 4</em></strong></div><span class="live-tag"><i></i> En vivo</span></div></section>
        <div class="workspace">
          <section class="left-column">
            <div class="panel take-panel" id="recepcion"><div class="panel-heading"><div><div class="step-tag">01 <span>·</span> RECEPCIÓN</div><h2>Tomar un turno</h2><p>Pulsa el botón y te damos tu número. No necesitas registrar datos personales.</p></div><div class="heading-icon">＋</div></div>
              <div class="help-note"><span>ⓘ</span><div><b>Aclaración en ventanilla.</b> Conserva tu folio; aparecerá automáticamente en la mesa disponible.</div></div>
              <div class="form-footer"><span>◉ &nbsp;Servicio: <b>Aclaración en ventanilla</b></span><button class="primary" (click)="createTicket()" [disabled]="busy">{{ busy ? 'Generando…' : 'Tomar turno' }} <span>→</span></button></div>
              <div class="error" *ngIf="error">{{ error }}</div>
              <div class="ticket-result" *ngIf="lastTicket"><div class="ticket-check">✓</div><div><small>TU TURNO</small><strong>{{ lastTicket.code }}</strong><span>Conserva este folio para identificarte.</span></div><div class="ticket-wait">{{ waitEstimate }}<small>espera estimada</small></div></div>
            </div>
            <div class="panel queue-panel"><div class="queue-header"><div><div class="step-tag">02 <span>·</span> FILA DE ATENCIÓN</div><h2>Próximos turnos</h2></div><span class="count-chip">{{ state?.waiting_count ?? 0 }} en espera</span></div><div class="queue-list" *ngIf="state?.waiting?.length; else emptyQueue"><div class="queue-row" *ngFor="let t of state?.waiting; let i = index"><div class="queue-number">{{ t.code }}</div><div class="queue-person"><b>Aclaración en ventanilla</b><small>Folio {{ t.code }}</small></div><div class="queue-position">{{ i === 0 ? 'Siguiente' : 'En espera' }}</div></div></div><ng-template #emptyQueue><div class="empty-queue"><span>✓</span><div><b>La fila está despejada</b><small>Los nuevos turnos aparecerán aquí.</small></div></div></ng-template></div>
          </section>
          <section class="panel desks-panel" id="atencion"><div class="desks-header"><div><div class="step-tag">03 <span>·</span> ATENCIÓN EN VENTANILLA</div><h2>Mesas de atención</h2><p>El siguiente turno se asigna automáticamente a una mesa libre.</p></div><button class="sound-toggle" (click)="enableSound()"><span>♫</span> {{ soundEnabled ? 'Campanita activada' : 'Activar campanita' }}</button></div>
            <div class="desk-grid"><article class="desk-card" *ngFor="let d of state?.desks"><div class="desk-top"><span>MESA {{ d.number }}</span><span [class.occupied-state]="d.ticket" class="desk-status"><i></i>{{ d.ticket ? 'Atendiendo' : 'Disponible' }}</span></div><div class="desk-body" *ngIf="d.ticket; else deskFree"><div class="desk-ticket">{{ d.ticket.code }}</div><div class="desk-service">Aclaración en ventanilla · Turno automático</div></div><ng-template #deskFree><div class="desk-free"><div class="desk-icon">⌂</div><b>Mesa libre</b><small>Esperando al siguiente turno</small></div></ng-template></article></div>
            <div class="auto-status"><span class="pulse"></span> Llamado, asignación y avance de turnos automáticos · actualización cada 2.5 segundos.</div>
            <div class="desk-foot"><span class="secure">⌑</span> Cada atención automática dura {{ state?.service_seconds ?? 30 }} segundos; al terminar, la mesa toma el turno siguiente.</div>
          </section>
        </div>
        <footer>© 2026 Vitalia Laboratorio Clínico <span>Atención con calidez, resultados con confianza.</span></footer>
      </div>
    </main>
  </div>`
})
class AppComponent implements OnInit {
  private api = inject(QueueApi);
  private audioContext: AudioContext | null = null;
  private previousDeskTickets: Map<number, string> | null = null;
  section: 'turnos' | 'atencion' = 'turnos'; soundEnabled = false;
  state: State | null = null; busy = false; error = ''; lastTicket: Ticket | null = null;
  today = new Intl.DateTimeFormat('es-MX', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }).format(new Date());
  get occupied() { return this.state?.desks.filter(d => !!d.ticket).length ?? 0; }
  get waitEstimate() { return `~${Math.max(1, Math.ceil((this.state?.waiting_count ?? 0) * (this.state?.service_seconds ?? 30) / 60))} min`; }
  ngOnInit() { this.refresh(); setInterval(() => this.refresh(), 2500); }
  refresh() { this.api.state().subscribe({ next: s => { this.detectDeskChanges(s); this.state = s; this.error = ''; }, error: () => this.error = 'No se pudo conectar con el servidor de turnos. Intenta de nuevo en unos segundos.' }); }
  goTo(section: 'turnos' | 'atencion') { this.section = section; document.getElementById(section)?.scrollIntoView({ behavior: 'smooth', block: 'start' }); }
  private prepareSound() { try { this.audioContext ??= new AudioContext(); void this.audioContext.resume(); this.soundEnabled = true; } catch { this.soundEnabled = false; } }
  enableSound() { this.prepareSound(); this.playBell(); }
  private playBell() {
    if (!this.soundEnabled || !this.audioContext) return;
    const context = this.audioContext, start = context.currentTime;
    for (const [offset, frequency] of [[0, 880], [0.16, 1174]] as const) {
      const oscillator = context.createOscillator(), gain = context.createGain(), time = start + offset;
      oscillator.type = 'sine'; oscillator.frequency.setValueAtTime(frequency, time);
      gain.gain.setValueAtTime(0.0001, time); gain.gain.exponentialRampToValueAtTime(0.12, time + 0.02); gain.gain.exponentialRampToValueAtTime(0.0001, time + 0.28);
      oscillator.connect(gain); gain.connect(context.destination); oscillator.start(time); oscillator.stop(time + 0.29);
    }
  }
  private detectDeskChanges(state: State) {
    if (this.previousDeskTickets) for (const desk of state.desks) {
      const current = desk.ticket?.id ?? '';
      if (current && this.previousDeskTickets.get(desk.number) !== current) this.playBell();
    }
    this.previousDeskTickets = new Map(state.desks.map(desk => [desk.number, desk.ticket?.id ?? '']));
  }
  createTicket() { this.prepareSound(); this.error = ''; this.busy = true; this.api.create().subscribe({ next: t => { this.lastTicket = t; this.busy = false; this.refresh(); }, error: e => { const message = e.error?.error ?? ''; this.error = message.toLowerCase().includes('nombre') ? 'La ventana de Python sigue usando la versión anterior. Deténla con Ctrl+C y vuelve a iniciar py -m backend.server.' : message || 'No se pudo generar el turno.'; this.busy = false; } }); }
}

bootstrapApplication(AppComponent, { providers: [provideHttpClient()] }).catch(err => console.error(err));
