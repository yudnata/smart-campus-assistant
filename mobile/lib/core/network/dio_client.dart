// ============================================================
// core/network/dio_client.dart
// Konfigurasi Dio HTTP client — shared di semua fitur
// ============================================================

import 'package:dio/dio.dart';
import 'package:pretty_dio_logger/pretty_dio_logger.dart';
import '../constants/api_constants.dart';

class DioClient {
  DioClient._(); // private constructor

  static Dio? _instance;

  /// Singleton Dio instance
  static Dio get instance {
    _instance ??= _createDio();
    return _instance!;
  }

  static Dio _createDio() {
    final dio = Dio(
      BaseOptions(
        connectTimeout: ApiConstants.connectTimeout,
        receiveTimeout: ApiConstants.receiveTimeout,
        sendTimeout: ApiConstants.sendTimeout,
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        validateStatus: (status) => status != null && status < 500,
      ),
    );

    // Logger hanya di development
    assert(() {
      dio.interceptors.add(
        PrettyDioLogger(
          requestHeader: true,
          requestBody: true,
          responseHeader: false,
          responseBody: true,
          compact: true,
        ),
      );
      return true;
    }());

    // Interceptor global untuk error handling
    dio.interceptors.add(
      InterceptorsWrapper(
        onError: (error, handler) {
          // Log error ke console di debug mode
          assert(() {
            // ignore: avoid_print
            print('[DioClient] Error: ${error.type} — ${error.message}');
            return true;
          }());
          handler.next(error);
        },
      ),
    );

    return dio;
  }
}
