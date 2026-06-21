import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:dio/dio.dart';

// Dio instance untuk auth
final authDioProvider = Provider<Dio>((ref) {
  return Dio(BaseOptions(
    baseUrl: 'http://10.0.2.2:3001/api', // Ubah sesuai environment (localhost 10.0.2.2 untuk emulator android)
    connectTimeout: const Duration(seconds: 10),
    receiveTimeout: const Duration(seconds: 10),
  ));
});

class AuthState {
  final bool isLoading;
  final bool isGuest;
  final bool isAuthenticated;
  final String? token;
  final Map<String, dynamic>? user;
  final String? error;

  AuthState({
    this.isLoading = false,
    this.isGuest = false,
    this.isAuthenticated = false,
    this.token,
    this.user,
    this.error,
  });

  AuthState copyWith({
    bool? isLoading,
    bool? isGuest,
    bool? isAuthenticated,
    String? token,
    Map<String, dynamic>? user,
    String? error,
  }) {
    return AuthState(
      isLoading: isLoading ?? this.isLoading,
      isGuest: isGuest ?? this.isGuest,
      isAuthenticated: isAuthenticated ?? this.isAuthenticated,
      token: token ?? this.token,
      user: user ?? this.user,
      error: error,
    );
  }
}

class AuthNotifier extends StateNotifier<AuthState> {
  final Dio dio;

  AuthNotifier(this.dio) : super(AuthState(isLoading: true)) {
    _initAuth();
  }

  Future<void> _initAuth() async {
    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString('auth_token');
    
    if (token != null && token.isNotEmpty) {
      await _fetchMe(token);
    } else {
      state = state.copyWith(isLoading: false, isGuest: true); // Default ke guest jika tidak ada token
    }
  }

  Future<void> _fetchMe(String token) async {
    try {
      final response = await dio.get(
        '/auth/me',
        options: Options(headers: {'Authorization': 'Bearer $token'}),
      );
      state = state.copyWith(
        isLoading: false,
        isAuthenticated: true,
        isGuest: false,
        token: token,
        user: response.data,
      );
    } catch (e) {
      // Token invalid / expired
      final prefs = await SharedPreferences.getInstance();
      await prefs.remove('auth_token');
      state = state.copyWith(isLoading: false, isGuest: true, isAuthenticated: false, token: null, user: null);
    }
  }

  Future<bool> login(String email, String password) async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      final response = await dio.post(
        '/auth/login',
        data: {'email': email, 'password': password},
      );
      final token = response.data['access_token'];
      
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('auth_token', token);
      
      await _fetchMe(token);
      return true;
    } catch (e) {
      String errorMessage = "Login gagal. Periksa kembali email & password Anda.";
      if (e is DioException && e.response != null) {
        errorMessage = e.response?.data['detail'] ?? errorMessage;
      }
      state = state.copyWith(isLoading: false, error: errorMessage);
      return false;
    }
  }

  Future<bool> register(String name, String email, String password) async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      await dio.post(
        '/auth/register',
        data: {'name': name, 'email': email, 'password': password},
      );
      state = state.copyWith(isLoading: false);
      return true;
    } catch (e) {
      String errorMessage = "Gagal mendaftar.";
      if (e is DioException && e.response != null) {
        errorMessage = e.response?.data['detail'] ?? errorMessage;
      }
      state = state.copyWith(isLoading: false, error: errorMessage);
      return false;
    }
  }

  Future<bool> verifyEmail(String email, String code) async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      await dio.post(
        '/auth/verify',
        data: {'email': email, 'code': code},
      );
      state = state.copyWith(isLoading: false);
      return true;
    } catch (e) {
      String errorMessage = "Kode verifikasi salah.";
      if (e is DioException && e.response != null) {
        errorMessage = e.response?.data['detail'] ?? errorMessage;
      }
      state = state.copyWith(isLoading: false, error: errorMessage);
      return false;
    }
  }

  void continueAsGuest() {
    state = state.copyWith(isGuest: true, isAuthenticated: false, user: null, token: null);
  }

  Future<void> logout() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('auth_token');
    state = state.copyWith(isAuthenticated: false, user: null, token: null, isGuest: true);
  }
}

final authProvider = StateNotifierProvider<AuthNotifier, AuthState>((ref) {
  return AuthNotifier(ref.watch(authDioProvider));
});
