// ============================================================
// features/chat/data/datasources/admin_remote_datasource.dart
// HTTP calls ke backend ingest API dengan progress callback
// ============================================================

import 'package:dio/dio.dart';
import '../../../../core/constants/api_constants.dart';
import '../../../../core/network/dio_client.dart';

class AdminRemoteDataSource {
  final Dio _dio;

  AdminRemoteDataSource({Dio? dio}) : _dio = dio ?? DioClient.instance;

  /// POST /api/ingest/file
  /// Mengunggah file (PDF/CSV/JSON) secara async dengan onProgress callback.
  Future<Map<String, dynamic>> uploadDocument({
    required List<int> fileBytes,
    required String filename,
    required String? token,
    String? prodi,
    String? bab,
    String? semester,
    String? tahunAkademik,
    bool overwriteOld = true,
    void Function(double progress)? onProgress,
  }) async {
    final formData = FormData.fromMap({
      'file': MultipartFile.fromBytes(
        fileBytes,
        filename: filename,
      ),
      if (prodi != null && prodi.isNotEmpty) 'prodi': prodi,
      if (bab != null && bab.isNotEmpty) 'bab': bab,
      if (semester != null && semester.isNotEmpty) 'semester': semester,
      if (tahunAkademik != null && tahunAkademik.isNotEmpty) 'tahun_akademik': tahunAkademik,
      'overwrite_old': overwriteOld.toString(),
    });

    final response = await _dio.post(
      '${ApiConstants.baseUrl}/api/ingest/file',
      data: formData,
      options: Options(
        headers: {
          'Accept': 'application/json',
          if (token != null) 'Authorization': 'Bearer $token',
        },
        receiveTimeout: const Duration(hours: 1), // Menonaktifkan batasan waktu (setel ke 1 jam) agar proses OCR PDF halaman panjang tidak terputus
      ),
      onSendProgress: (sent, total) {
        if (onProgress != null && total > 0) {
          onProgress(sent / total);
        }
      },
    );

    // Karena validateStatus di DioClient membiarkan status < 500 lolos ke response:
    if (response.statusCode == 200) {
      return response.data as Map<String, dynamic>;
    }

    throw DioException(
      requestOptions: response.requestOptions,
      response: response,
      message: response.data?['detail'] ?? 'Gagal mengunggah dokumen (${response.statusCode})',
    );
  }

  /// POST /api/ingest/preview-file
  /// Mengirim file (PDF/CSV/JSON) secara async dengan onProgress callback untuk mendapatkan pratinjau chunk.
  Future<Map<String, dynamic>> previewDocument({
    required List<int> fileBytes,
    required String filename,
    required String? token,
    String? prodi,
    String? bab,
    String? semester,
    String? tahunAkademik,
    void Function(double progress)? onProgress,
  }) async {
    final formData = FormData.fromMap({
      'file': MultipartFile.fromBytes(
        fileBytes,
        filename: filename,
      ),
      if (prodi != null && prodi.isNotEmpty) 'prodi': prodi,
      if (bab != null && bab.isNotEmpty) 'bab': bab,
      if (semester != null && semester.isNotEmpty) 'semester': semester,
      if (tahunAkademik != null && tahunAkademik.isNotEmpty) 'tahun_akademik': tahunAkademik,
    });

    final response = await _dio.post(
      '${ApiConstants.baseUrl}/api/ingest/preview-file',
      data: formData,
      options: Options(
        headers: {
          'Accept': 'application/json',
          if (token != null) 'Authorization': 'Bearer $token',
        },
        receiveTimeout: const Duration(hours: 1),
      ),
      onSendProgress: (sent, total) {
        if (onProgress != null && total > 0) {
          onProgress(sent / total);
        }
      },
    );

    if (response.statusCode == 200) {
      return response.data as Map<String, dynamic>;
    }

    throw DioException(
      requestOptions: response.requestOptions,
      response: response,
      message: response.data?['detail'] ?? 'Gagal mempratinjau dokumen (${response.statusCode})',
    );
  }

  /// POST /api/ingest/confirm-save
  /// Menyimpan chunk yang sudah diverifikasi ke database RAG.
  Future<Map<String, dynamic>> confirmSaveDocument({
    required List<dynamic> chunks,
    required String docType,
    required String? token,
    bool overwriteOld = true,
  }) async {
    final response = await _dio.post(
      '${ApiConstants.baseUrl}/api/ingest/confirm-save',
      data: {
        'chunks': chunks,
        'doc_type': docType,
        'overwrite_old': overwriteOld,
      },
      options: Options(
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
          if (token != null) 'Authorization': 'Bearer $token',
        },
        receiveTimeout: const Duration(hours: 1),
      ),
    );

    if (response.statusCode == 200) {
      return response.data as Map<String, dynamic>;
    }

    throw DioException(
      requestOptions: response.requestOptions,
      response: response,
      message: response.data?['detail'] ?? 'Gagal menyimpan dokumen (${response.statusCode})',
    );
  }

  /// GET /api/ingest/documents
  /// Mengambil daftar berkas yang telah disimpan di database RAG
  Future<List<dynamic>> getIngestedDocuments({required String? token}) async {
    final response = await _dio.get(
      '${ApiConstants.baseUrl}/api/ingest/documents',
      options: Options(
        headers: {
          'Accept': 'application/json',
          if (token != null) 'Authorization': 'Bearer $token',
        },
      ),
    );

    if (response.statusCode == 200) {
      return response.data as List<dynamic>;
    }

    throw DioException(
      requestOptions: response.requestOptions,
      response: response,
      message: response.data?['detail'] ?? 'Gagal memuat daftar dokumen',
    );
  }

  /// DELETE /api/ingest/documents?source_file=...
  /// Menghapus semua chunk yang terkait dengan nama berkas tertentu
  Future<Map<String, dynamic>> deleteDocument({required String sourceFile, required String? token}) async {
    final response = await _dio.delete(
      '${ApiConstants.baseUrl}/api/ingest/documents',
      queryParameters: {
        'source_file': sourceFile,
      },
      options: Options(
        headers: {
          'Accept': 'application/json',
          if (token != null) 'Authorization': 'Bearer $token',
        },
      ),
    );

    if (response.statusCode == 200) {
      return response.data as Map<String, dynamic>;
    }

    throw DioException(
      requestOptions: response.requestOptions,
      response: response,
      message: response.data?['detail'] ?? 'Gagal menghapus dokumen',
    );
  }
}
