// ============================================================
// features/chat/presentation/screens/admin_panel_screen.dart
// Screen Panel Admin untuk unggah dan proses dokumen akademik
// ============================================================

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:file_picker/file_picker.dart';
import 'package:gap/gap.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../auth/providers/auth_provider.dart';
import '../../data/datasources/admin_remote_datasource.dart';

class AdminPanelScreen extends ConsumerStatefulWidget {
  const AdminPanelScreen({super.key});

  @override
  ConsumerState<AdminPanelScreen> createState() => _AdminPanelScreenState();
}

class _AdminPanelScreenState extends ConsumerState<AdminPanelScreen> {
  final _prodiController = TextEditingController();
  final _babController = TextEditingController();
  bool _overwriteOld = true;
  
  PlatformFile? _selectedFile;
  bool _isUploading = false;
  double _uploadProgress = 0.0;
  String? _statusMessage;

  final _adminDataSource = AdminRemoteDataSource();
  
  List<dynamic> _ingestedDocs = [];
  bool _isLoadingDocs = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _loadIngestedDocuments();
    });
  }

  Future<void> _loadIngestedDocuments() async {
    setState(() => _isLoadingDocs = true);
    final token = ref.read(authProvider).token;
    try {
      final docs = await _adminDataSource.getIngestedDocuments(token: token);
      setState(() {
        _ingestedDocs = docs;
        _isLoadingDocs = false;
      });
    } catch (e) {
      setState(() => _isLoadingDocs = false);
    }
  }

  Future<void> _deleteDocument(String filename) async {
    final token = ref.read(authProvider).token;
    try {
      await _adminDataSource.deleteDocument(sourceFile: filename, token: token);
      _loadIngestedDocuments();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Berhasil menghapus berkas "$filename"'),
            backgroundColor: AppTheme.successColor,
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Gagal menghapus berkas: $e'),
            backgroundColor: AppTheme.errorColor,
          ),
        );
      }
    }
  }

  void _showDeleteConfirmation(String filename) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: AppTheme.surfaceCard,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(20),
          side: const BorderSide(color: AppTheme.surfaceBorder),
        ),
        title: const Text(
          'Konfirmasi Hapus',
          style: TextStyle(fontFamily: 'Quicksand', fontWeight: FontWeight.bold, color: AppTheme.textPrimary),
        ),
        content: Text(
          'Apakah Anda yakin ingin menghapus dokumen "$filename" beserta seluruh chunk dan vektor terkait dari database RAG?',
          style: const TextStyle(fontFamily: 'Quicksand', color: AppTheme.textSecondary),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Batal', style: TextStyle(fontFamily: 'Quicksand', color: AppTheme.textSecondary)),
          ),
          TextButton(
            onPressed: () {
              Navigator.pop(ctx);
              _deleteDocument(filename);
            },
            child: const Text('Hapus', style: TextStyle(fontFamily: 'Quicksand', fontWeight: FontWeight.bold, color: AppTheme.errorColor)),
          ),
        ],
      ),
    );
  }

  @override
  void dispose() {
    _prodiController.dispose();
    _babController.dispose();
    super.dispose();
  }

  Future<void> _pickDocument() async {
    try {
      final result = await FilePicker.platform.pickFiles(
        type: FileType.custom,
        allowedExtensions: ['pdf', 'csv', 'json', 'png', 'jpg', 'jpeg', 'webp'],
        withData: true, // Wajib diaktifkan untuk mengambil bytes file di memori (mendukung Web, Android, iOS)
      );

      if (result != null && result.files.isNotEmpty) {
        setState(() {
          _selectedFile = result.files.first;
          _statusMessage = null;
        });
      }
    } catch (e) {
      setState(() {
        _statusMessage = 'Gagal memilih file: $e';
      });
    }
  }

  Future<void> _uploadAndProcess() async {
    if (_selectedFile == null) {
      setState(() {
        _statusMessage = 'Pilih file terlebih dahulu!';
      });
      return;
    }

    final fileBytes = _selectedFile!.bytes;
    if (fileBytes == null) {
      setState(() {
        _statusMessage = 'Tidak dapat membaca data file. Coba lagi.';
      });
      return;
    }

    setState(() {
      _isUploading = true;
      _uploadProgress = 0.0;
      _statusMessage = 'Menghubungkan ke server...';
    });

    final token = ref.read(authProvider).token;

    try {
      final response = await _adminDataSource.uploadDocument(
        fileBytes: fileBytes,
        filename: _selectedFile!.name,
        token: token,
        prodi: _prodiController.text.trim(),
        bab: _babController.text.trim(),
        overwriteOld: _overwriteOld,
        onProgress: (progress) {
          setState(() {
            _uploadProgress = progress;
            if (progress < 1.0) {
              _statusMessage = 'Mengunggah file: ${(progress * 100).toStringAsFixed(0)}%';
            } else {
              _statusMessage = 'File terkirim! Server sedang mengekstrak teks & membuat representasi vektor (RAG). Harap tunggu...';
            }
          });
        },
      );

      final chunksCount = response['chunks_added'] ?? 0;

      setState(() {
        _isUploading = false;
        _uploadProgress = 1.0;
        _selectedFile = null;
        _statusMessage = null;
      });
      _loadIngestedDocuments();

      if (mounted) {
        _showSuccessDialog(chunksCount);
      }
    } catch (e) {
      setState(() {
        _isUploading = false;
        _statusMessage = 'Error: $e';
      });
    }
  }

  void _showSuccessDialog(dynamic chunksCount) {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => AlertDialog(
        backgroundColor: AppTheme.surfaceCard,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(20),
          side: const BorderSide(color: AppTheme.surfaceBorder),
        ),
        title: const Row(
          children: [
            Icon(Icons.check_circle_rounded, color: Colors.green, size: 28),
            SizedBox(width: 8),
            Text('Proses Berhasil', style: TextStyle(fontFamily: 'Quicksand', fontWeight: FontWeight.bold, color: AppTheme.textPrimary)),
          ],
        ),
        content: Text(
          'Dokumen berhasil diunggah, diekstrak, dan dipecah menjadi $chunksCount chunk ke database RAG.',
          style: const TextStyle(fontFamily: 'Quicksand', color: AppTheme.textSecondary),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Tutup', style: TextStyle(fontFamily: 'Quicksand', fontWeight: FontWeight.bold, color: AppTheme.accentPrimary)),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final canPop = Navigator.canPop(context);
    
    return Scaffold(
      backgroundColor: AppTheme.backgroundLight,
      appBar: AppBar(
        title: const Text(
          'Panel Admin Ingest',
          style: TextStyle(fontFamily: 'Quicksand', fontWeight: FontWeight.bold, color: AppTheme.textPrimary),
        ),
        centerTitle: true,
        backgroundColor: Colors.transparent,
        elevation: 0,
        leading: canPop
            ? IconButton(
                icon: const Icon(Icons.arrow_back_ios_new_rounded, color: AppTheme.textSecondary),
                onPressed: () => Navigator.pop(context),
              )
            : const Center(
                child: Icon(Icons.admin_panel_settings_rounded, color: AppTheme.accentPrimary, size: 28),
              ),
        actions: [
          IconButton(
            icon: const Icon(Icons.logout_rounded, color: AppTheme.errorColor),
            tooltip: 'Keluar (Logout)',
            onPressed: () {
              ref.read(authProvider.notifier).logout();
            },
          ),
          const SizedBox(width: 12),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Header Info Card
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: AppTheme.accentPrimary.withOpacity(0.08),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: AppTheme.accentPrimary.withOpacity(0.2)),
              ),
              child: const Row(
                children: [
                  Icon(Icons.info_outline_rounded, color: AppTheme.accentPrimary, size: 24),
                  SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      'Unggah dokumen pedoman akademik baru (.pdf, .csv, .json) untuk diproses menjadi representasi vektor secara otomatis.',
                      style: TextStyle(fontFamily: 'Quicksand', fontSize: 13, color: AppTheme.textSecondary, fontWeight: FontWeight.w500),
                    ),
                  ),
                ],
              ),
            ),
            const Gap(24),

            // Form Inputs Card
            Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: AppTheme.surfaceBorder),
                boxShadow: [
                  BoxShadow(color: Colors.black.withOpacity(0.02), blurRadius: 10, offset: const Offset(0, 4)),
                ],
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'METADATA DOKUMEN (OPSIONAL)',
                    style: TextStyle(fontFamily: 'Quicksand', fontSize: 11, fontWeight: FontWeight.bold, color: AppTheme.textMuted, letterSpacing: 0.8),
                  ),
                  const Gap(16),

                  // Program Studi Input
                  TextField(
                    controller: _prodiController,
                    enabled: !_isUploading,
                    style: const TextStyle(fontFamily: 'Quicksand'),
                    decoration: InputDecoration(
                      labelText: 'Program Studi (Prodi)',
                      labelStyle: const TextStyle(fontFamily: 'Quicksand'),
                      prefixIcon: const Icon(Icons.school_outlined, size: 20),
                      border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                    ),
                  ),
                  const Gap(16),

                  // Bab Input
                  TextField(
                    controller: _babController,
                    enabled: !_isUploading,
                    style: const TextStyle(fontFamily: 'Quicksand'),
                    decoration: InputDecoration(
                      labelText: 'Bab Dokumen (e.g. Bab 1 / Bab 2)',
                      labelStyle: const TextStyle(fontFamily: 'Quicksand'),
                      prefixIcon: const Icon(Icons.menu_book_outlined, size: 20),
                      border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                    ),
                  ),
                  const Gap(16),

                  // Overwrite Switch Row
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Tulis Ulang (Overwrite)',
                            style: TextStyle(fontFamily: 'Quicksand', fontWeight: FontWeight.w600, color: AppTheme.textPrimary),
                          ),
                          Text(
                            'Hapus dokumen lama dengan nama yang sama',
                            style: TextStyle(fontFamily: 'Quicksand', fontSize: 11, color: AppTheme.textMuted),
                          ),
                        ],
                      ),
                      Switch(
                        value: _overwriteOld,
                        activeColor: AppTheme.accentPrimary,
                        onChanged: _isUploading
                            ? null
                            : (val) {
                                setState(() {
                                  _overwriteOld = val;
                                });
                              },
                      ),
                    ],
                  ),
                ],
              ),
            ),
            const Gap(24),

            // File Picker Action Area
            GestureDetector(
              onTap: _isUploading ? null : _pickDocument,
              child: Container(
                padding: const EdgeInsets.symmetric(vertical: 36, horizontal: 16),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(
                    color: _selectedFile != null ? AppTheme.accentPrimary.withOpacity(0.5) : AppTheme.surfaceBorder,
                    width: 1.5,
                    style: _selectedFile != null ? BorderStyle.solid : BorderStyle.solid,
                  ),
                  boxShadow: [
                    BoxShadow(color: Colors.black.withOpacity(0.01), blurRadius: 8, offset: const Offset(0, 2)),
                  ],
                ),
                child: Column(
                  children: [
                    Icon(
                      _selectedFile != null ? Icons.insert_drive_file_rounded : Icons.cloud_upload_outlined,
                      size: 48,
                      color: _selectedFile != null ? AppTheme.accentPrimary : AppTheme.textMuted,
                    ),
                    const Gap(12),
                    Text(
                      _selectedFile != null ? _selectedFile!.name : 'Pilih File Dokumen',
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        fontFamily: 'Quicksand',
                        fontWeight: FontWeight.bold,
                        color: _selectedFile != null ? AppTheme.textPrimary : AppTheme.textSecondary,
                      ),
                    ),
                    if (_selectedFile != null) ...[
                      const Gap(4),
                      Text(
                        'Ukuran: ${(_selectedFile!.size / 1024).toStringAsFixed(1)} KB',
                        style: const TextStyle(fontFamily: 'Quicksand', fontSize: 11, color: AppTheme.textMuted),
                      ),
                    ] else ...[
                      const Gap(4),
                      const Text(
                        'Format file yang didukung: PDF, CSV, JSON, Gambar (PNG/JPG/WEBP)',
                        style: TextStyle(fontFamily: 'Quicksand', fontSize: 11, color: AppTheme.textMuted),
                      ),
                    ]
                  ],
                ),
              ),
            ),
            const Gap(24),

            // Ingest Progress Indicator
            if (_isUploading) ...[
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: AppTheme.surfaceBorder),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text(
                          _uploadProgress < 1.0 ? 'Mengunggah Berkas...' : 'Memproses Data & RAG...',
                          style: const TextStyle(fontFamily: 'Quicksand', fontWeight: FontWeight.bold, color: AppTheme.textPrimary, fontSize: 13),
                        ),
                        Text(
                          _uploadProgress < 1.0 ? '${(_uploadProgress * 100).toStringAsFixed(0)}%' : 'Mengekstrak...',
                          style: const TextStyle(fontFamily: 'Quicksand', fontWeight: FontWeight.bold, color: AppTheme.accentPrimary, fontSize: 13),
                        ),
                      ],
                    ),
                    const Gap(8),
                    LinearProgressIndicator(
                      value: _uploadProgress < 1.0 ? _uploadProgress : null,
                      backgroundColor: AppTheme.surfaceBorder,
                      color: AppTheme.accentPrimary,
                      minHeight: 8,
                      borderRadius: BorderRadius.circular(4),
                    ),
                  ],
                ),
              ),
              const Gap(24),
            ],

            // Status message (Success/Error description)
            if (_statusMessage != null) ...[
              Text(
                _statusMessage!,
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontFamily: 'Quicksand',
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                  color: _statusMessage!.startsWith('Error') ? AppTheme.errorColor : AppTheme.textSecondary,
                ),
              ),
              const Gap(24),
            ],

            // Process Button
             ElevatedButton(
              onPressed: _isUploading || _selectedFile == null ? null : _uploadAndProcess,
              style: ElevatedButton.styleFrom(
                backgroundColor: AppTheme.accentPrimary,
                disabledBackgroundColor: AppTheme.surfaceBorder,
                elevation: 0,
                padding: const EdgeInsets.symmetric(vertical: 16),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(24)),
              ),
              child: const Text(
                'Unggah & Proses Dokumen',
                style: TextStyle(fontFamily: 'Quicksand', fontWeight: FontWeight.bold, fontSize: 15, color: Colors.white),
              ),
            ),
            const Gap(32),
            const Divider(),
            const Gap(16),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text(
                  'DAFTAR DOKUMEN DI DATABASE RAG',
                  style: TextStyle(fontFamily: 'Quicksand', fontSize: 11, fontWeight: FontWeight.bold, color: AppTheme.textMuted, letterSpacing: 0.8),
                ),
                IconButton(
                  icon: const Icon(Icons.refresh_rounded, size: 20, color: AppTheme.accentPrimary),
                  tooltip: 'Segarkan',
                  onPressed: _isLoadingDocs ? null : _loadIngestedDocuments,
                ),
              ],
            ),
            const Gap(12),
            if (_isLoadingDocs)
              const Center(
                child: Padding(
                  padding: EdgeInsets.symmetric(vertical: 24),
                  child: CircularProgressIndicator(),
                ),
              )
            else if (_ingestedDocs.isEmpty)
              Container(
                padding: const EdgeInsets.symmetric(vertical: 36, horizontal: 16),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: AppTheme.surfaceBorder),
                ),
                child: const Text(
                  'Belum ada dokumen yang terserap di database RAG.',
                  textAlign: TextAlign.center,
                  style: TextStyle(fontFamily: 'Quicksand', color: AppTheme.textMuted, fontSize: 13),
                ),
              )
            else
              ListView.separated(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                itemCount: _ingestedDocs.length,
                separatorBuilder: (context, index) => const Gap(12),
                itemBuilder: (context, index) {
                  final doc = _ingestedDocs[index];
                  final filename = doc['source_file'] as String;
                  final docType = doc['doc_type'] as String;
                  final chunksCount = doc['total_chunks'] as int;
                  
                  return Container(
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(16),
                      border: Border.all(color: AppTheme.surfaceBorder),
                    ),
                    child: Row(
                      children: [
                        Container(
                          width: 40,
                          height: 40,
                          decoration: BoxDecoration(
                            color: AppTheme.accentPrimary.withOpacity(0.08),
                            borderRadius: BorderRadius.circular(12),
                          ),
                          child: Icon(
                            docType.contains('image') || docType.contains('ocr')
                                ? Icons.image_outlined
                                : Icons.description_outlined,
                            color: AppTheme.accentPrimary,
                            size: 22,
                          ),
                        ),
                        const Gap(12),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                filename,
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: const TextStyle(
                                  fontFamily: 'Quicksand',
                                  fontWeight: FontWeight.bold,
                                  color: AppTheme.textPrimary,
                                  fontSize: 14,
                                ),
                              ),
                              const Gap(4),
                              Row(
                                children: [
                                  Container(
                                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                                    decoration: BoxDecoration(
                                      color: Colors.green.withOpacity(0.1),
                                      borderRadius: BorderRadius.circular(12),
                                    ),
                                    child: Text(
                                      '$chunksCount chunk',
                                      style: const TextStyle(
                                        fontFamily: 'Quicksand',
                                        fontSize: 11,
                                        fontWeight: FontWeight.bold,
                                        color: Colors.green,
                                      ),
                                    ),
                                  ),
                                  const Gap(8),
                                  Text(
                                    docType,
                                    style: const TextStyle(
                                      fontFamily: 'Quicksand',
                                      fontSize: 11,
                                      color: AppTheme.textMuted,
                                    ),
                                  ),
                                ],
                              ),
                            ],
                          ),
                        ),
                        IconButton(
                          icon: const Icon(Icons.delete_outline_rounded, color: AppTheme.errorColor),
                          onPressed: () => _showDeleteConfirmation(filename),
                        ),
                      ],
                    ),
                  );
                },
              ),
          ],
        ),
      ),
    );
  }
}
