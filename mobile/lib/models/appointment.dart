class Appointment {
  final int    id;
  final String patientName;
  final String patientPhone;
  final String? patientEmail;
  final String therapyType;
  final String date;   // 'YYYY-MM-DD'
  final String slot;   // 'HH:MM'
  final String status; // 'pending' | 'confirmed' | 'cancelled'
  final int    price;
  final String? notes;

  const Appointment({
    required this.id,
    required this.patientName,
    required this.patientPhone,
    this.patientEmail,
    required this.therapyType,
    required this.date,
    required this.slot,
    required this.status,
    required this.price,
    this.notes,
  });

  factory Appointment.fromJson(Map<String, dynamic> j) => Appointment(
    id:           j['id'],
    patientName:  j['patient_name'],
    patientPhone: j['patient_phone'],
    patientEmail: j['patient_email'],
    therapyType:  j['therapy_type'],
    date:         j['date'],
    slot:         j['slot'],
    status:       j['status'],
    price:        j['price'],
    notes:        j['notes'],
  );

  Appointment copyWith({String? status}) => Appointment(
    id:           id,
    patientName:  patientName,
    patientPhone: patientPhone,
    patientEmail: patientEmail,
    therapyType:  therapyType,
    date:         date,
    slot:         slot,
    status:       status ?? this.status,
    price:        price,
    notes:        notes,
  );

  static const therapyLabels = {
    'individual':   'Terapia Individual',
    'pareja':       'Terapia en Pareja',
    'familia':      'Terapia Familiar',
    'adolescentes': 'Terapia para Adolescentes',
    'online':       'Terapia en Línea',
  };

  String get therapyLabel => therapyLabels[therapyType] ?? therapyType;

  String get formattedSlot {
    final h = int.parse(slot.split(':')[0]);
    if (h == 0)  return '12:00 AM';
    if (h < 12)  return '$h:00 AM';
    if (h == 12) return '12:00 PM';
    return '${h - 12}:00 PM';
  }
}
