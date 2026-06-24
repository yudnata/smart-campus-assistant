import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../core/theme/app_theme.dart';
import '../../providers/auth_provider.dart';

class VerifyEmailScreen extends ConsumerStatefulWidget {
  final String email;
  const VerifyEmailScreen({super.key, required this.email});

  @override
  ConsumerState<VerifyEmailScreen> createState() => _VerifyEmailScreenState();
}

class _VerifyEmailScreenState extends ConsumerState<VerifyEmailScreen> {
  final _codeController = TextEditingController();

  void _handleVerify() async {
    final code = _codeController.text.trim();
    if (code.isEmpty) return;

    final success = await ref.read(authProvider.notifier).verifyEmail(widget.email, code);
    if (success && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Email berhasil diverifikasi! Silakan login.'), backgroundColor: AppTheme.successColor),
      );
      Navigator.pop(context); // Kembali ke LoginScreen
    } else if (mounted) {
      final error = ref.read(authProvider).error;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(error ?? 'Verifikasi gagal.'), backgroundColor: AppTheme.errorColor),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authProvider);

    return Scaffold(
      backgroundColor: AppTheme.backgroundLight,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_rounded, color: AppTheme.textPrimary),
          onPressed: () => Navigator.pop(context),
        ),
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Icon(Icons.mark_email_unread_rounded, size: 80, color: AppTheme.accentPrimary),
              const SizedBox(height: 24),
              const Text(
                'Verifikasi Email',
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontFamily: 'Quicksand',
                  fontSize: 28,
                  fontWeight: FontWeight.bold,
                  color: AppTheme.textPrimary,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                'Kode verifikasi 6-digit telah dikirim (ke terminal backend) untuk ${widget.email}.',
                textAlign: TextAlign.center,
                style: const TextStyle(
                  fontFamily: 'Quicksand',
                  fontSize: 14,
                  color: AppTheme.textSecondary,
                ),
              ),
              const SizedBox(height: 48),

              // Code Field
              TextField(
                controller: _codeController,
                keyboardType: TextInputType.number,
                textAlign: TextAlign.center,
                style: const TextStyle(fontSize: 24, letterSpacing: 8, fontWeight: FontWeight.bold),
                decoration: InputDecoration(
                  hintText: '000000',
                  filled: true,
                  fillColor: AppTheme.surfaceCard,
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(16),
                    borderSide: const BorderSide(color: AppTheme.surfaceBorder),
                  ),
                ),
              ),
              const SizedBox(height: 32),

              // Verify Button
              SizedBox(
                height: 54,
                child: ElevatedButton(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppTheme.accentPrimary,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                  ),
                  onPressed: authState.isLoading ? null : _handleVerify,
                  child: authState.isLoading
                      ? const CircularProgressIndicator(color: Colors.white)
                      : const Text(
                          'Verifikasi',
                          style: TextStyle(
                            fontFamily: 'Quicksand',
                            fontSize: 16,
                            fontWeight: FontWeight.bold,
                            color: Colors.white,
                          ),
                        ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
