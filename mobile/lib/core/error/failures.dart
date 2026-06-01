// ============================================================
// core/error/failures.dart
// Definisi semua tipe kegagalan menggunakan Fpdart pattern
// ============================================================

import 'package:equatable/equatable.dart';

/// Base class untuk semua failure — dipakai dengan Either<Failure, T>
abstract class Failure extends Equatable {
  final String message;
  const Failure(this.message);

  @override
  List<Object?> get props => [message];
}

/// Kegagalan jaringan / server tidak bisa dihubungi
class NetworkFailure extends Failure {
  const NetworkFailure([super.message = 'Tidak dapat terhubung ke server. Pastikan backend berjalan.']);
}

/// Server mengembalikan error HTTP (4xx / 5xx)
class ServerFailure extends Failure {
  final int? statusCode;
  const ServerFailure(super.message, {this.statusCode});

  @override
  List<Object?> get props => [message, statusCode];
}

/// Timeout saat request
class TimeoutFailure extends Failure {
  const TimeoutFailure([super.message = 'Request timeout. Coba lagi.']);
}

/// Error parsing JSON response
class ParseFailure extends Failure {
  const ParseFailure([super.message = 'Gagal memproses respons dari server.']);
}

/// File upload gagal / tidak valid
class FileFailure extends Failure {
  const FileFailure(super.message);
}

/// Tidak ada konten yang ditemukan (retrieval kosong)
class NotFoundFailure extends Failure {
  const NotFoundFailure([super.message = 'Tidak ditemukan informasi relevan di pedoman akademik.']);
}
