import 'package:flutter/material.dart';
import 'package:flutter_slidable/flutter_slidable.dart';
import 'package:intl/intl.dart';
import '../config/theme.dart';
import '../models/appointment.dart';
import '../services/api_service.dart';
import 'new_appointment_screen.dart';

class DayDetailScreen extends StatefulWidget {
  final String  pin;
  final String  dateStr;
  final String? availability;

  const DayDetailScreen({
    super.key,
    required this.pin,
    required this.dateStr,
    this.availability,
  });

  @override
  State<DayDetailScreen> createState() => _DayDetailScreenState();
}

class _DayDetailScreenState extends State<DayDetailScreen> {
  late final ApiService _api;
  List<Appointment> _appointments = [];
  bool _blocked = false;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _api     = ApiService(widget.pin);
    _blocked = widget.availability == 'unavailable' &&
               _isManuallyBlocked();
    _load();
  }

  // Heurística: si availability es unavailable pero hay horarios libres
  // en el día, está bloqueado manualmente (no por citas llenas).
  bool _isManuallyBlocked() => widget.availability == 'unavailable';

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final appts = await _api.getAppointments(date: widget.dateStr);
      final blocked = await _api.getBlockedDays();
      final isBlocked = blocked.any((b) => b['date'] == widget.dateStr);
      if (mounted) setState(() {
        _appointments = appts;
        _blocked      = isBlocked;
        _loading      = false;
      });
    } catch (_) {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _toggleBlock() async {
    try {
      if (_blocked) {
        await _api.unblockDay(widget.dateStr);
      } else {
        await _showBlockDialog();
        return; // el diálogo llama _load al confirmar
      }
      await _load();
    } catch (e) {
      _showError(e.toString());
    }
  }

  Future<void> _showBlockDialog() async {
    final reasonCtrl = TextEditingController();
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: kNavyLight,
        title: const Text('Bloquear día',
          style: TextStyle(color: kWhite)),
        content: TextField(
          controller:  reasonCtrl,
          decoration:  const InputDecoration(
            labelText: 'Motivo (opcional)',
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Cancelar',
              style: TextStyle(color: kWhiteDim)),
          ),
          ElevatedButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Bloquear'),
          ),
        ],
      ),
    );
    if (confirmed == true) {
      await _api.blockDay(
        widget.dateStr,
        reason: reasonCtrl.text.trim().isEmpty ? null : reasonCtrl.text.trim(),
      );
      await _load();
    }
  }

  Future<void> _updateStatus(Appointment appt, String newStatus) async {
    try {
      final updated = await _api.updateStatus(appt.id, newStatus);
      setState(() {
        final idx = _appointments.indexWhere((a) => a.id == appt.id);
        if (idx != -1) _appointments[idx] = updated;
      });
    } catch (e) {
      _showError(e.toString());
    }
  }

  void _showError(String msg) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(msg), backgroundColor: kRed),
    );
  }

  String _formatDate(String dateStr) {
    final d = DateTime.parse(dateStr);
    final months = [
      '', 'enero','febrero','marzo','abril','mayo','junio',
      'julio','agosto','septiembre','octubre','noviembre','diciembre',
    ];
    final days = ['', 'lunes','martes','miércoles',
                  'jueves','viernes','sábado','domingo'];
    return '${days[d.weekday]}, ${d.day} de ${months[d.month]}';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(_formatDate(widget.dateStr).toUpperCase()),
        actions: [
          IconButton(
            icon: const Icon(Icons.add),
            tooltip: 'Agregar cita',
            onPressed: _blocked ? null : () => Navigator.push(
              context,
              MaterialPageRoute(
                builder: (_) => NewAppointmentScreen(
                  pin:         widget.pin,
                  preselectedDate: widget.dateStr,
                ),
              ),
            ).then((_) => _load()),
          ),
        ],
      ),
      body: _loading
        ? const Center(child: CircularProgressIndicator(color: kWhiteDim))
        : Column(
            children: [
              // Toggle bloquear día
              _BlockToggle(
                blocked:  _blocked,
                onToggle: _toggleBlock,
              ),
              const Divider(height: 1),

              // Lista de citas
              Expanded(
                child: _appointments.isEmpty
                  ? Center(
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          const Icon(Icons.event_available,
                            color: kWhiteDim, size: 48),
                          const SizedBox(height: 12),
                          Text(
                            _blocked
                              ? 'Día bloqueado'
                              : 'Sin citas agendadas',
                            style: Theme.of(context).textTheme.bodyMedium,
                          ),
                        ],
                      ),
                    )
                  : ListView.separated(
                      padding: const EdgeInsets.all(16),
                      itemCount: _appointments.length,
                      separatorBuilder: (_, __) => const SizedBox(height: 8),
                      itemBuilder: (_, i) => _AppointmentTile(
                        appointment: _appointments[i],
                        onConfirm:   () => _updateStatus(_appointments[i], 'confirmed'),
                        onCancel:    () => _updateStatus(_appointments[i], 'cancelled'),
                      ),
                    ),
              ),
            ],
          ),
    );
  }
}

// ── Subwidgets ────────────────────────────────────────────────

class _BlockToggle extends StatelessWidget {
  final bool blocked;
  final VoidCallback onToggle;
  const _BlockToggle({required this.blocked, required this.onToggle});

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onToggle,
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
        child: Row(
          children: [
            Icon(
              blocked ? Icons.lock : Icons.lock_open,
              color: blocked ? kRed : kGreen,
              size: 20,
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Text(
                blocked
                  ? 'Día bloqueado — toca para desbloquear'
                  : 'Día activo — toca para bloquear',
                style: TextStyle(
                  color:  blocked ? kRed : kGreen,
                  fontSize: 13,
                ),
              ),
            ),
            Switch(
              value:          !blocked,
              onChanged:      (_) => onToggle(),
              activeColor:    kGreen,
              inactiveThumbColor: kRed,
              inactiveTrackColor: kRed.withOpacity(0.3),
            ),
          ],
        ),
      ),
    );
  }
}

class _AppointmentTile extends StatelessWidget {
  final Appointment appointment;
  final VoidCallback onConfirm;
  final VoidCallback onCancel;
  const _AppointmentTile({
    required this.appointment,
    required this.onConfirm,
    required this.onCancel,
  });

  Color get _statusColor {
    switch (appointment.status) {
      case 'confirmed': return kGreen;
      case 'cancelled': return kRed;
      default:          return kYellow;
    }
  }

  String get _statusLabel {
    switch (appointment.status) {
      case 'confirmed': return 'Confirmada';
      case 'cancelled': return 'Cancelada';
      default:          return 'Pendiente';
    }
  }

  @override
  Widget build(BuildContext context) {
    return Slidable(
      endActionPane: ActionPane(
        motion: const DrawerMotion(),
        children: [
          if (appointment.status != 'confirmed')
            SlidableAction(
              onPressed: (_) => onConfirm(),
              backgroundColor: kGreen,
              foregroundColor: kNavy,
              icon:  Icons.check,
              label: 'Confirmar',
            ),
          if (appointment.status != 'cancelled')
            SlidableAction(
              onPressed: (_) => onCancel(),
              backgroundColor: kRed,
              foregroundColor: kWhite,
              icon:  Icons.close,
              label: 'Cancelar',
            ),
        ],
      ),
      child: Card(
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Row(
            children: [
              // Hora
              Container(
                width: 54,
                alignment: Alignment.center,
                child: Text(
                  appointment.formattedSlot,
                  style: const TextStyle(
                    color: kWhite, fontSize: 13, fontWeight: FontWeight.w700,
                  ),
                  textAlign: TextAlign.center,
                ),
              ),
              Container(
                width: 1, height: 40,
                margin: const EdgeInsets.symmetric(horizontal: 12),
                color: const Color(0x33FFFFFF),
              ),
              // Info
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(appointment.patientName,
                      style: const TextStyle(
                        color: kWhite, fontWeight: FontWeight.w600,
                      )),
                    const SizedBox(height: 2),
                    Text(appointment.therapyLabel,
                      style: const TextStyle(
                        color: kWhiteDim, fontSize: 12,
                      )),
                    const SizedBox(height: 2),
                    Text(appointment.patientPhone,
                      style: const TextStyle(
                        color: Color(0x80FFFFFF), fontSize: 11,
                      )),
                  ],
                ),
              ),
              // Estado + precio
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 8, vertical: 3,
                    ),
                    decoration: BoxDecoration(
                      color:        _statusColor.withOpacity(0.15),
                      borderRadius: BorderRadius.circular(3),
                      border:       Border.all(
                        color: _statusColor.withOpacity(0.5),
                      ),
                    ),
                    child: Text(
                      _statusLabel,
                      style: TextStyle(
                        color: _statusColor, fontSize: 10,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    '\$${appointment.price.toString().replaceAllMapped(RegExp(r'(\d{1,3})(?=(\d{3})+(?!\d))'), (m) => '${m[1]},')}',
                    style: const TextStyle(
                      color: kWhiteDim, fontSize: 12,
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
