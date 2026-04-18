import 'dart:convert';
import 'package:http/http.dart' as http;
import '../config/api_config.dart';
import '../models/appointment.dart';

class ApiService {
  final String pin;
  ApiService(this.pin);

  Map<String, String> get _headers => {
    'Content-Type':  'application/json',
    'Authorization': 'Bearer $pin',
  };

  // ── Auth ────────────────────────────────────────────────────

  Future<bool> login() async {
    final res = await http.post(
      Uri.parse('$kApiBase/admin/login'),
      headers: _headers,
    );
    return res.statusCode == 200;
  }

  // ── Appointments ────────────────────────────────────────────

  Future<List<Appointment>> getAppointments({String? date}) async {
    final uri = Uri.parse('$kApiBase/admin/appointments').replace(
      queryParameters: date != null ? {'date': date} : null,
    );
    final res = await http.get(uri, headers: _headers);
    _checkStatus(res);
    final List data = jsonDecode(utf8.decode(res.bodyBytes));
    return data.map((j) => Appointment.fromJson(j)).toList();
  }

  Future<Appointment> createAppointment(Map<String, dynamic> payload) async {
    final res = await http.post(
      Uri.parse('$kApiBase/admin/appointments'),
      headers: _headers,
      body: jsonEncode(payload),
    );
    _checkStatus(res);
    return Appointment.fromJson(jsonDecode(utf8.decode(res.bodyBytes)));
  }

  Future<Appointment> updateStatus(int id, String status) async {
    final res = await http.patch(
      Uri.parse('$kApiBase/admin/appointments/$id/status'),
      headers: _headers,
      body: jsonEncode({'status': status}),
    );
    _checkStatus(res);
    return Appointment.fromJson(jsonDecode(utf8.decode(res.bodyBytes)));
  }

  // ── Calendar ────────────────────────────────────────────────

  Future<Map<String, String>> getCalendar(int year, int month) async {
    final res = await http.get(
      Uri.parse('$kApiBase/appointments/calendar?year=$year&month=$month'),
      headers: _headers,
    );
    _checkStatus(res);
    final Map<String, dynamic> raw = jsonDecode(utf8.decode(res.bodyBytes));
    return raw.map((k, v) => MapEntry(k, v.toString()));
  }

  Future<List<Map<String, dynamic>>> getSlots(String date) async {
    final res = await http.get(
      Uri.parse('$kApiBase/appointments/slots?date=$date'),
      headers: _headers,
    );
    _checkStatus(res);
    final data = jsonDecode(utf8.decode(res.bodyBytes));
    return List<Map<String, dynamic>>.from(data['slots']);
  }

  // ── Blocked days ────────────────────────────────────────────

  Future<List<Map<String, dynamic>>> getBlockedDays() async {
    final res = await http.get(
      Uri.parse('$kApiBase/admin/blocked-days'),
      headers: _headers,
    );
    _checkStatus(res);
    return List<Map<String, dynamic>>.from(jsonDecode(utf8.decode(res.bodyBytes)));
  }

  Future<void> blockDay(String date, {String? reason}) async {
    final res = await http.post(
      Uri.parse('$kApiBase/admin/blocked-days'),
      headers: _headers,
      body: jsonEncode({'date': date, 'reason': reason}),
    );
    _checkStatus(res);
  }

  Future<void> unblockDay(String date) async {
    final res = await http.delete(
      Uri.parse('$kApiBase/admin/blocked-days/$date'),
      headers: _headers,
    );
    if (res.statusCode != 204) _checkStatus(res);
  }

  // ── Helper ──────────────────────────────────────────────────

  void _checkStatus(http.Response res) {
    if (res.statusCode >= 400) {
      String msg = 'Error ${res.statusCode}';
      try {
        final body = jsonDecode(utf8.decode(res.bodyBytes));
        msg = body['detail'] ?? msg;
      } catch (_) {}
      throw ApiException(msg, res.statusCode);
    }
  }
}

class ApiException implements Exception {
  final String message;
  final int    statusCode;
  ApiException(this.message, this.statusCode);

  @override
  String toString() => message;
}
