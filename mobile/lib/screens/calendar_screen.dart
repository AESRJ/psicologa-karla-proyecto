import 'package:flutter/material.dart';
import 'package:table_calendar/table_calendar.dart';
import 'package:intl/intl.dart';
import '../config/theme.dart';
import '../services/api_service.dart';
import 'day_detail_screen.dart';
import 'new_appointment_screen.dart';

class CalendarScreen extends StatefulWidget {
  final String pin;
  const CalendarScreen({super.key, required this.pin});

  @override
  State<CalendarScreen> createState() => _CalendarScreenState();
}

class _CalendarScreenState extends State<CalendarScreen> {
  late final ApiService _api;
  DateTime _focusedDay   = DateTime.now();
  DateTime? _selectedDay;
  Map<String, String> _availability = {};
  bool _loadingCal = true;

  @override
  void initState() {
    super.initState();
    _api = ApiService(widget.pin);
    _loadCalendar();
  }

  Future<void> _loadCalendar() async {
    setState(() => _loadingCal = true);
    try {
      final data = await _api.getCalendar(
        _focusedDay.year, _focusedDay.month,
      );
      if (mounted) setState(() { _availability = data; _loadingCal = false; });
    } catch (_) {
      if (mounted) setState(() => _loadingCal = false);
    }
  }

  Color _dayColor(String dateStr) {
    switch (_availability[dateStr]) {
      case 'unavailable': return kRed;
      case 'limited':     return kYellow;
      case 'available':   return kGreen;
      default:            return const Color(0x33FFFFFF);
    }
  }

  void _onDaySelected(DateTime selected, DateTime focused) {
    setState(() {
      _selectedDay = selected;
      _focusedDay  = focused;
    });
    final dateStr = DateFormat('yyyy-MM-dd').format(selected);
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => DayDetailScreen(
          pin:     widget.pin,
          dateStr: dateStr,
          availability: _availability[dateStr],
        ),
      ),
    ).then((_) => _loadCalendar()); // refrescar al volver
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('AGENDA'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadCalendar,
            tooltip: 'Actualizar',
          ),
        ],
      ),
      body: Column(
        children: [
          // Leyenda
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                _legendItem(kGreen,  'Disponible'),
                const SizedBox(width: 16),
                _legendItem(kYellow, 'Poca disponibilidad'),
                const SizedBox(width: 16),
                _legendItem(kRed,    'Sin disponibilidad'),
              ],
            ),
          ),

          // Calendario
          _loadingCal
            ? const Padding(
                padding: EdgeInsets.all(32),
                child: CircularProgressIndicator(color: kWhiteDim),
              )
            : TableCalendar(
                firstDay:       DateTime(2024),
                lastDay:        DateTime(2030, 12, 31),
                focusedDay:     _focusedDay,
                selectedDayPredicate: (d) => isSameDay(_selectedDay, d),
                onDaySelected:  _onDaySelected,
                onPageChanged:  (focused) {
                  _focusedDay = focused;
                  _loadCalendar();
                },
                locale: 'es_MX',
                startingDayOfWeek: StartingDayOfWeek.monday,
                headerStyle: const HeaderStyle(
                  formatButtonVisible:  false,
                  titleCentered:        true,
                  titleTextStyle: TextStyle(
                    color: kWhite, fontWeight: FontWeight.w600,
                    letterSpacing: 1,
                  ),
                  leftChevronIcon:  Icon(Icons.chevron_left,  color: kWhiteDim),
                  rightChevronIcon: Icon(Icons.chevron_right, color: kWhiteDim),
                ),
                daysOfWeekStyle: const DaysOfWeekStyle(
                  weekdayStyle: TextStyle(color: kWhiteDim, fontSize: 12),
                  weekendStyle: TextStyle(color: kWhiteDim, fontSize: 12),
                ),
                calendarStyle: const CalendarStyle(
                  outsideDaysVisible:  false,
                  defaultTextStyle:    TextStyle(color: kWhite),
                  weekendTextStyle:    TextStyle(color: kWhite),
                  todayDecoration:     BoxDecoration(
                    color: kBlueBtn, shape: BoxShape.circle,
                  ),
                  selectedDecoration:  BoxDecoration(
                    color: kWhite, shape: BoxShape.circle,
                  ),
                  selectedTextStyle:   TextStyle(
                    color: kNavy, fontWeight: FontWeight.w700,
                  ),
                ),
                calendarBuilders: CalendarBuilders(
                  defaultBuilder: (ctx, day, _) => _dayCell(day),
                  outsideBuilder:  (ctx, day, _) => const SizedBox(),
                ),
              ),

          const Divider(height: 1),

          // Instrucción
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 12),
            child: Text(
              'Toca un día para ver las citas',
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => Navigator.push(
          context,
          MaterialPageRoute(
            builder: (_) => NewAppointmentScreen(pin: widget.pin),
          ),
        ).then((_) => _loadCalendar()),
        icon:  const Icon(Icons.add),
        label: const Text('Nueva cita'),
      ),
    );
  }

  Widget _dayCell(DateTime day) {
    final dateStr = DateFormat('yyyy-MM-dd').format(day);
    final color   = _dayColor(dateStr);
    final isPast  = day.isBefore(DateTime.now().subtract(const Duration(days: 1)));

    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            '${day.day}',
            style: TextStyle(
              color: isPast ? const Color(0x55FFFFFF) : kWhite,
              fontSize: 13,
            ),
          ),
          const SizedBox(height: 2),
          Container(
            width: 6, height: 6,
            decoration: BoxDecoration(
              color:  isPast ? Colors.transparent : color,
              shape:  BoxShape.circle,
            ),
          ),
        ],
      ),
    );
  }

  Widget _legendItem(Color color, String label) => Row(
    children: [
      Container(
        width: 8, height: 8,
        decoration: BoxDecoration(color: color, shape: BoxShape.circle),
      ),
      const SizedBox(width: 4),
      Text(label, style: const TextStyle(color: kWhiteDim, fontSize: 10)),
    ],
  );
}
