import 'package:flutter/material.dart';

// ── Paleta — mismos colores que el sitio web ──────────────────
const kNavy      = Color(0xFF0D2461);
const kNavyLight = Color(0xFF14306E);
const kNavyDark  = Color(0xFF091A47);
const kWhite     = Colors.white;
const kWhiteDim  = Color(0xB3FFFFFF); // 70% opacity
const kGreen     = Color(0xFF4ADE80);
const kYellow    = Color(0xFFFBBF24);
const kRed       = Color(0xFFF87171);
const kBlueBtn   = Color(0xFF1A4FD6);

ThemeData buildTheme() {
  return ThemeData(
    useMaterial3: true,
    scaffoldBackgroundColor: kNavy,
    colorScheme: ColorScheme.dark(
      primary:   kBlueBtn,
      secondary: kWhiteDim,
      surface:   kNavyLight,
      error:     kRed,
    ),
    appBarTheme: const AppBarTheme(
      backgroundColor: kNavyDark,
      foregroundColor: kWhite,
      elevation: 0,
      centerTitle: true,
      titleTextStyle: TextStyle(
        color:       kWhite,
        fontSize:    16,
        fontWeight:  FontWeight.w600,
        letterSpacing: 1.5,
      ),
    ),
    cardTheme: CardTheme(
      color:        kNavyLight,
      elevation:    0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(6),
        side: const BorderSide(color: Color(0x33FFFFFF)),
      ),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled:      true,
      fillColor:   kNavyLight,
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(4),
        borderSide:   const BorderSide(color: Color(0x33FFFFFF)),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(4),
        borderSide:   const BorderSide(color: Color(0x33FFFFFF)),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(4),
        borderSide:   const BorderSide(color: kWhite),
      ),
      labelStyle:    const TextStyle(color: kWhiteDim),
      hintStyle:     const TextStyle(color: Color(0x66FFFFFF)),
    ),
    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        backgroundColor: kBlueBtn,
        foregroundColor: kWhite,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(4)),
        padding: const EdgeInsets.symmetric(vertical: 14),
        textStyle: const TextStyle(letterSpacing: 1, fontWeight: FontWeight.w600),
      ),
    ),
    textTheme: const TextTheme(
      bodyLarge:   TextStyle(color: kWhite),
      bodyMedium:  TextStyle(color: kWhiteDim),
      bodySmall:   TextStyle(color: Color(0x80FFFFFF)),
      titleLarge:  TextStyle(color: kWhite,    fontWeight: FontWeight.w700),
      titleMedium: TextStyle(color: kWhite,    fontWeight: FontWeight.w600),
      labelSmall:  TextStyle(color: kWhiteDim, letterSpacing: 2),
    ),
    dividerColor: const Color(0x1AFFFFFF),
    floatingActionButtonTheme: const FloatingActionButtonThemeData(
      backgroundColor: kBlueBtn,
      foregroundColor: kWhite,
    ),
  );
}
