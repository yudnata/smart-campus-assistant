// ============================================================
// features/chat/data/datasources/chat_remote_datasource.dart
// HTTP calls ke Express.js backend menggunakan DioClient
// ============================================================

import 'package:dio/dio.dart';
import '../../../../core/constants/api_constants.dart';
import '../../../../core/network/dio_client.dart';

class ChatRemoteDataSource {
  final Dio _dio;

  ChatRemoteDataSource({Dio? dio}) : _dio = dio ?? DioClient.instance;

  /// POST /api/chat
  /// Throws [DioException] jika terjadi error jaringan/server
  Future<Map<String, dynamic>> sendMessage({
    required String question,
    int topK = 5,
  }) async {
    final response = await _dio.post(
      ApiConstants.chat,
      data: {
        'question': question,
        'topK': topK,
      },
    );

    if (response.statusCode == 200) {
      return response.data as Map<String, dynamic>;
    }

    throw DioException(
      requestOptions: response.requestOptions,
      response: response,
      message: response.data?['error'] ?? 'Server error ${response.statusCode}',
    );
  }
}
