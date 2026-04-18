import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../config/theme.dart';
import '../services/api_service.dart';
import 'calendar_screen.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _pinController = TextEditingController();
  bool _loading = false;
  String? _error;

  Future<void> _login() async {
    final pin = _pinController.text.trim();
    if (pin.isEmpty) return;

    setState(() { _loading = true; _error = null; });

    try {
      final ok = await ApiService(pin).login();
      if (!mounted) return;
      if (ok) {
        final prefs = await SharedPreferences.getInstance();
        await prefs.setString('admin_pin', pin);
        Navigator.pushReplacement(
          context,
          MaterialPageRoute(builder: (_) => CalendarScreen(pin: pin)),
        );
      } else {
        setState(() { _error = 'PIN incorrecto.'; });
      }
    } catch (e) {
      setState(() { _error = 'No se pudo conectar al servidor.'; });
    } finally {
      if (mounted) setState(() { _loading = false; });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(32),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                // Logo / título
                const SizedBox(height: 16),
                Text(
                  'PSICÓLOGA',
                  style: Theme.of(context).textTheme.labelSmall?.copyWith(
                    fontSize: 11, letterSpacing: 4,
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  'Karla Zermeño',
                  style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    fontSize: 26, letterSpacing: 2,
                  ),
                ),
                const SizedBox(height: 48),

                // Card de login
                Container(
                  padding: const EdgeInsets.all(28),
                  decoration: BoxDecoration(
                    color:        kNavyLight,
                    borderRadius: BorderRadius.circular(6),
                    border: Border.all(color: const Color(0x33FFFFFF)),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Text(
                        'ACCESO ADMINISTRADOR',
                        style: Theme.of(context).textTheme.labelSmall,
                        textAlign: TextAlign.center,
                      ),
                      const SizedBox(height: 24),
                      TextField(
                        controller:    _pinController,
                        obscureText:   true,
                        keyboardType:  TextInputType.visiblePassword,
                        textAlign:     TextAlign.center,
                        style: const TextStyle(
                          color: kWhite, fontSize: 22, letterSpacing: 8,
                        ),
                        decoration: const InputDecoration(
                          hintText: '• • • • • •',
                          labelText: 'PIN de acceso',
                        ),
                        onSubmitted: (_) => _login(),
                      ),
                      if (_error != null) ...[
                        const SizedBox(height: 12),
                        Text(
                          _error!,
                          style: const TextStyle(color: kRed, fontSize: 13),
                          textAlign: TextAlign.center,
                        ),
                      ],
                      const SizedBox(height: 20),
                      SizedBox(
                        width: double.infinity,
                        child: ElevatedButton(
                          onPressed: _loading ? null : _login,
                          child: _loading
                            ? const SizedBox(
                                height: 18, width: 18,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2, color: kWhite,
                                ),
                              )
                            : const Text('ENTRAR'),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  @override
  void dispose() {
    _pinController.dispose();
    super.dispose();
  }
}
