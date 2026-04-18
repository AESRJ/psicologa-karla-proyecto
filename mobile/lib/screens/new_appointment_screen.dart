import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../config/theme.dart';
import '../services/api_service.dart';

const _therapyOptions = [
  {'value': 'individual',   'label': 'Terapia Individual',          'price': 600},
  {'value': 'pareja',       'label': 'Terapia en Pareja',           'price': 800},
  {'value': 'familia',      'label': 'Terapia Familiar',            'price': 1000},
  {'value': 'adolescentes', 'label': 'Terapia para Adolescentes',   'price': 600},
  {'value': 'online',       'label': 'Terapia en Línea',            'price': 600},
];

class NewAppointmentScreen extends StatefulWidget {
  final String  pin;
  final String? preselectedDate;
  const NewAppointmentScreen({
    super.key,
    required this.pin,
    this.preselectedDate,
  });

  @override
  State<NewAppointmentScreen> createState() => _NewAppointmentScreenState();
}

class _NewAppointmentScreenState extends State<NewAppointmentScreen> {
  late final ApiService _api;
  final _formKey   = GlobalKey<FormState>();
  final _nameCtrl  = TextEditingController();
  final _phoneCtrl = TextEditingController();
  final _emailCtrl = TextEditingController();
  final _notesCtrl = TextEditingController();

  String? _selectedDate;
  String? _selectedSlot;
  String  _selectedTherapy = 'individual';
  List<Map<String, dynamic>> _slots = [];
  bool _loadingSlots = false;
  bool _saving       = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _api = ApiService(widget.pin);
    if (widget.preselectedDate != null) {
      _selectedDate = widget.preselectedDate;
      _loadSlots();
    }
  }

  Future<void> _pickDate() async {
    final picked = await showDatePicker(
      context:      context,
      initialDate:  _selectedDate != null
        ? DateTime.parse(_selectedDate!)
        : DateTime.now(),
      firstDate:    DateTime.now(),
      lastDate:     DateTime(2030, 12, 31),
      builder: (ctx, child) => Theme(
        data: Theme.of(ctx).copyWith(
          colorScheme: const ColorScheme.dark(
            primary:   kBlueBtn,
            surface:   kNavyLight,
            onSurface: kWhite,
          ),
        ),
        child: child!,
      ),
    );
    if (picked != null) {
      setState(() {
        _selectedDate = DateFormat('yyyy-MM-dd').format(picked);
        _selectedSlot = null;
        _slots        = [];
      });
      _loadSlots();
    }
  }

  Future<void> _loadSlots() async {
    if (_selectedDate == null) return;
    setState(() { _loadingSlots = true; _selectedSlot = null; });
    try {
      final slots = await _api.getSlots(_selectedDate!);
      if (mounted) setState(() {
        _slots        = slots;
        _loadingSlots = false;
      });
    } catch (_) {
      if (mounted) setState(() => _loadingSlots = false);
    }
  }

  Future<void> _save() async {
    if (!_formKey.currentState!.validate()) return;
    if (_selectedDate == null) {
      setState(() => _error = 'Selecciona una fecha.');
      return;
    }
    if (_selectedSlot == null) {
      setState(() => _error = 'Selecciona un horario.');
      return;
    }

    setState(() { _saving = true; _error = null; });

    try {
      final therapy = _therapyOptions
        .firstWhere((t) => t['value'] == _selectedTherapy);

      await _api.createAppointment({
        'patient_name':  _nameCtrl.text.trim(),
        'patient_phone': _phoneCtrl.text.trim(),
        'patient_email': _emailCtrl.text.trim().isEmpty
          ? null : _emailCtrl.text.trim(),
        'therapy_type':  _selectedTherapy,
        'date':          _selectedDate,
        'slot':          _selectedSlot,
        'price':         therapy['price'],
        'notes':         _notesCtrl.text.trim().isEmpty
          ? null : _notesCtrl.text.trim(),
      });

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content:         Text('Cita agendada correctamente'),
            backgroundColor: kGreen,
          ),
        );
        Navigator.pop(context);
      }
    } catch (e) {
      setState(() { _error = e.toString(); _saving = false; });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('NUEVA CITA')),
      body: Form(
        key: _formKey,
        child: ListView(
          padding: const EdgeInsets.all(20),
          children: [

            // ── Fecha ──
            _sectionLabel('FECHA'),
            InkWell(
              onTap: _pickDate,
              child: Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 14, vertical: 14,
                ),
                decoration: BoxDecoration(
                  color:        kNavyLight,
                  borderRadius: BorderRadius.circular(4),
                  border:       Border.all(color: const Color(0x33FFFFFF)),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.calendar_today,
                      color: kWhiteDim, size: 18),
                    const SizedBox(width: 12),
                    Text(
                      _selectedDate ?? 'Seleccionar fecha',
                      style: TextStyle(
                        color: _selectedDate != null ? kWhite : kWhiteDim,
                      ),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 20),

            // ── Horario ──
            _sectionLabel('HORARIO'),
            if (_loadingSlots)
              const Padding(
                padding: EdgeInsets.symmetric(vertical: 12),
                child: Center(child: CircularProgressIndicator(
                  color: kWhiteDim, strokeWidth: 2,
                )),
              )
            else if (_slots.isEmpty)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 8),
                child: Text(
                  _selectedDate == null
                    ? 'Selecciona una fecha primero'
                    : 'Sin horarios disponibles',
                  style: const TextStyle(color: kWhiteDim, fontSize: 13),
                ),
              )
            else
              Wrap(
                spacing: 8, runSpacing: 8,
                children: _slots.map((s) {
                  final time      = s['time'] as String;
                  final available = s['available'] as bool;
                  final selected  = _selectedSlot == time;
                  final h = int.parse(time.split(':')[0]);
                  final label = h < 12
                    ? '$h:00 AM'
                    : h == 12 ? '12:00 PM' : '${h - 12}:00 PM';
                  return ChoiceChip(
                    label:          Text(label),
                    selected:       selected,
                    onSelected:     available
                      ? (_) => setState(() => _selectedSlot = time)
                      : null,
                    selectedColor:  kBlueBtn,
                    disabledColor:  kRed.withOpacity(0.15),
                    backgroundColor: kNavyLight,
                    labelStyle: TextStyle(
                      color: available
                        ? (selected ? kWhite : kWhiteDim)
                        : kRed.withOpacity(0.5),
                      fontSize: 12,
                    ),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(4),
                      side: BorderSide(
                        color: selected
                          ? kBlueBtn
                          : available
                            ? const Color(0x33FFFFFF)
                            : kRed.withOpacity(0.3),
                      ),
                    ),
                  );
                }).toList(),
              ),
            const SizedBox(height: 20),

            // ── Modalidad ──
            _sectionLabel('MODALIDAD'),
            ..._therapyOptions.map((t) {
              final selected = _selectedTherapy == t['value'];
              return Padding(
                padding: const EdgeInsets.only(bottom: 6),
                child: InkWell(
                  borderRadius: BorderRadius.circular(4),
                  onTap: () => setState(
                    () => _selectedTherapy = t['value'] as String,
                  ),
                  child: Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 14, vertical: 12,
                    ),
                    decoration: BoxDecoration(
                      color: selected
                        ? kBlueBtn.withOpacity(0.2)
                        : kNavyLight,
                      borderRadius: BorderRadius.circular(4),
                      border: Border.all(
                        color: selected
                          ? kBlueBtn
                          : const Color(0x33FFFFFF),
                      ),
                    ),
                    child: Row(
                      children: [
                        Expanded(
                          child: Text(t['label'] as String,
                            style: TextStyle(
                              color: selected ? kWhite : kWhiteDim,
                            )),
                        ),
                        Text(
                          '\$${t['price']} MXN',
                          style: TextStyle(
                            color: selected ? kWhite : kWhiteDim,
                            fontSize: 12,
                          ),
                        ),
                        if (selected) ...[
                          const SizedBox(width: 8),
                          const Icon(Icons.check_circle,
                            color: kBlueBtn, size: 18),
                        ],
                      ],
                    ),
                  ),
                ),
              );
            }),
            const SizedBox(height: 20),

            // ── Datos del paciente ──
            _sectionLabel('DATOS DEL PACIENTE'),
            TextFormField(
              controller: _nameCtrl,
              decoration: const InputDecoration(labelText: 'Nombre completo'),
              style: const TextStyle(color: kWhite),
              validator: (v) =>
                (v == null || v.trim().length < 2) ? 'Requerido' : null,
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller:  _phoneCtrl,
              decoration:  const InputDecoration(labelText: 'Teléfono'),
              keyboardType: TextInputType.phone,
              style:        const TextStyle(color: kWhite),
              validator: (v) =>
                (v == null || v.trim().length < 7) ? 'Requerido' : null,
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller:  _emailCtrl,
              decoration:  const InputDecoration(
                labelText: 'Correo electrónico (opcional)',
              ),
              keyboardType: TextInputType.emailAddress,
              style:        const TextStyle(color: kWhite),
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: _notesCtrl,
              decoration: const InputDecoration(
                labelText: 'Notas (opcional)',
              ),
              maxLines: 2,
              style: const TextStyle(color: kWhite),
            ),
            const SizedBox(height: 28),

            // ── Error ──
            if (_error != null)
              Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: Text(
                  _error!,
                  style: const TextStyle(color: kRed, fontSize: 13),
                  textAlign: TextAlign.center,
                ),
              ),

            // ── Botón guardar ──
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: _saving ? null : _save,
                child: _saving
                  ? const SizedBox(
                      height: 18, width: 18,
                      child: CircularProgressIndicator(
                        strokeWidth: 2, color: kWhite,
                      ),
                    )
                  : const Text('AGENDAR CITA'),
              ),
            ),
            const SizedBox(height: 40),
          ],
        ),
      ),
    );
  }

  Widget _sectionLabel(String text) => Padding(
    padding: const EdgeInsets.only(bottom: 10),
    child: Text(text,
      style: const TextStyle(
        color: kWhiteDim, fontSize: 10,
        letterSpacing: 3, fontWeight: FontWeight.w600,
      )),
  );

  @override
  void dispose() {
    _nameCtrl.dispose();
    _phoneCtrl.dispose();
    _emailCtrl.dispose();
    _notesCtrl.dispose();
    super.dispose();
  }
}
