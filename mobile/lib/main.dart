import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:intl/date_symbol_data_local.dart';
import 'config/theme.dart';
import 'screens/login_screen.dart';
import 'screens/calendar_screen.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await initializeDateFormatting('es_MX', null);

  // Pantalla vertical solamente
  await SystemChrome.setPreferredOrientations([
    DeviceOrientation.portraitUp,
    DeviceOrientation.portraitDown,
  ]);

  // Barra de estado transparente
  SystemChrome.setSystemUIOverlayStyle(const SystemUiOverlayStyle(
    statusBarColor:            Colors.transparent,
    statusBarIconBrightness:   Brightness.light,
  ));

  // Verificar si ya hay sesión guardada
  final prefs = await SharedPreferences.getInstance();
  final savedPin = prefs.getString('admin_pin');

  runApp(KarlaAdminApp(savedPin: savedPin));
}

class KarlaAdminApp extends StatelessWidget {
  final String? savedPin;
  const KarlaAdminApp({super.key, this.savedPin});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title:        'Karla Psicóloga — Admin',
      theme:        buildTheme(),
      debugShowCheckedModeBanner: false,
      home: savedPin != null
        ? CalendarScreen(pin: savedPin!)
        : const LoginScreen(),
    );
  }
}
