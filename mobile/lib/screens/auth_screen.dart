/// WardWatch - Authentication Screen
/// Phone OTP authentication with Firebase Phone Auth.
library;

import 'dart:async';
import 'package:flutter/material.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:cloud_functions/cloud_functions.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'discovery_map_screen.dart';

class AuthScreen extends StatefulWidget {
  const AuthScreen({super.key});

  @override
  State<AuthScreen> createState() => _AuthScreenState();
}

class _AuthScreenState extends State<AuthScreen> {
  final _auth = FirebaseAuth.instance;
  final _secureStorage = const FlutterSecureStorage();

  // Controllers
  final _phoneController = TextEditingController();
  final _otpController = TextEditingController();

  // State
  bool _isLoading = false;
  bool _codeSent = false;
  String _verificationId = '';
  int? _resendToken;
  String _errorMessage = '';

  // OTP resend cooldown
  int _cooldownSeconds = 0;
  Timer? _cooldownTimer;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Verify Your Phone'),
        backgroundColor: const Color(0xFF1565C0),
        foregroundColor: Colors.white,
        automaticallyImplyLeading: false,
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24.0),
          child: _codeSent ? _buildOTPInput() : _buildPhoneInput(),
        ),
      ),
    );
  }

  Widget _buildPhoneInput() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const SizedBox(height: 32),
        const Text(
          'Enter Your Mobile Number',
          style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 8),
        const Text(
          'We will send a one-time password to verify your identity.',
          style: TextStyle(color: Colors.black54),
        ),
        const SizedBox(height: 32),
        TextFormField(
          controller: _phoneController,
          keyboardType: TextInputType.phone,
          decoration: InputDecoration(
            labelText: 'Phone Number',
            prefixText: '+91 ',
            hintText: '9876543210',
            border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
          ),
          maxLength: 10,
        ),
        if (_errorMessage.isNotEmpty) ...[
          const SizedBox(height: 8),
          Text(_errorMessage, style: const TextStyle(color: Colors.red, fontSize: 14)),
        ],
        const Spacer(),
        SizedBox(
          width: double.infinity,
          child: ElevatedButton(
            onPressed: _isLoading ? null : _sendOTP,
            style: ElevatedButton.styleFrom(
              backgroundColor: const Color(0xFF1565C0),
              foregroundColor: Colors.white,
              padding: const EdgeInsets.symmetric(vertical: 16),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            ),
            child: _isLoading
                ? const SizedBox(
                    height: 20, width: 20,
                    child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2),
                  )
                : const Text('Send OTP', style: TextStyle(fontSize: 18)),
          ),
        ),
        const SizedBox(height: 16),
      ],
    );
  }

  Widget _buildOTPInput() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const SizedBox(height: 32),
        const Text(
          'Enter OTP',
          style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
        ),
        Text(
          'OTP sent to +91 ${_phoneController.text}',
          style: const TextStyle(color: Colors.black54),
        ),
        const SizedBox(height: 32),
        TextFormField(
          controller: _otpController,
          keyboardType: TextInputType.number,
          maxLength: 6,
          decoration: InputDecoration(
            labelText: 'OTP Code',
            hintText: '------',
            border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
          ),
        ),
        if (_errorMessage.isNotEmpty) ...[
          const SizedBox(height: 8),
          Text(_errorMessage, style: const TextStyle(color: Colors.red, fontSize: 14)),
        ],
        const SizedBox(height: 16),
        // Resend OTP button with cooldown
        _cooldownSeconds > 0
            ? Text(
                'Resend OTP in ${_cooldownSeconds}s',
                style: const TextStyle(color: Colors.black38),
              )
            : TextButton(
                onPressed: _sendOTP,
                child: const Text('Resend OTP'),
              ),
        const Spacer(),
        SizedBox(
          width: double.infinity,
          child: ElevatedButton(
            onPressed: _isLoading ? null : _verifyOTP,
            style: ElevatedButton.styleFrom(
              backgroundColor: const Color(0xFF1565C0),
              foregroundColor: Colors.white,
              padding: const EdgeInsets.symmetric(vertical: 16),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            ),
            child: _isLoading
                ? const SizedBox(
                    height: 20, width: 20,
                    child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2),
                  )
                : const Text('Verify OTP', style: TextStyle(fontSize: 18)),
          ),
        ),
        const SizedBox(height: 16),
      ],
    );
  }

  Future<void> _sendOTP() async {
    final phone = _phoneController.text.trim();
    if (phone.length != 10) {
      setState(() => _errorMessage = 'Please enter a valid 10-digit phone number.');
      return;
    }

    setState(() {
      _isLoading = true;
      _errorMessage = '';
    });

    try {
      await _auth.verifyPhoneNumber(
        phoneNumber: '+91$phone',
        timeout: const Duration(seconds: 60),
        forceResendingToken: _resendToken,
        verificationCompleted: (PhoneAuthCredential credential) async {
          // Auto-verification (Android only)
          await _signInWithCredential(credential);
        },
        verificationFailed: (FirebaseAuthException e) {
          setState(() {
            _isLoading = false;
            _errorMessage = _mapAuthError(e.code);
          });
        },
        codeSent: (String verificationId, int? resendToken) {
          setState(() {
            _verificationId = verificationId;
            _resendToken = resendToken;
            _codeSent = true;
            _isLoading = false;
          });
          _startCooldown();
        },
        codeAutoRetrievalTimeout: (String verificationId) {
          _verificationId = verificationId;
        },
      );
    } catch (e) {
      setState(() {
        _isLoading = false;
        _errorMessage = 'Failed to send OTP. Please try again.';
      });
    }
  }

  Future<void> _verifyOTP() async {
    final otp = _otpController.text.trim();
    if (otp.length != 6) {
      setState(() => _errorMessage = 'Please enter the 6-digit OTP.');
      return;
    }

    setState(() {
      _isLoading = true;
      _errorMessage = '';
    });

    try {
      final credential = PhoneAuthProvider.credential(
        verificationId: _verificationId,
        smsCode: otp,
      );
      await _signInWithCredential(credential);
    } on FirebaseAuthException catch (e) {
      setState(() {
        _isLoading = false;
        _errorMessage = _mapAuthError(e.code);
      });
    } catch (e) {
      setState(() {
        _isLoading = false;
        _errorMessage = 'Verification failed. Please try again.';
      });
    }
  }

  Future<void> _signInWithCredential(PhoneAuthCredential credential) async {
    try {
      // Link or sign in
      final currentUser = _auth.currentUser;
      if (currentUser != null && currentUser.isAnonymous) {
        await currentUser.linkWithCredential(credential);
      } else {
        await _auth.signInWithCredential(credential);
      }

      // Call Cloud Function to set phone_verified custom claim
      final callable = FirebaseFunctions.instance.httpsCallable(
        'verifyPhone-verifyPhoneAndUpgradeRole',
      );
      await callable.call();

      // Force token refresh to pick up new custom claims
      await _auth.currentUser?.getIdToken(true);

      // Store verification timestamp in secure storage
      await _secureStorage.write(
        key: 'phone_verified_at',
        value: DateTime.now().toIso8601String(),
      );

      if (!mounted) return;

      // Navigate to discovery map
      Navigator.of(context).pushReplacement(
        MaterialPageRoute(builder: (_) => const DiscoveryMapScreen()),
      );
    } catch (e) {
      setState(() {
        _isLoading = false;
        _errorMessage = 'Sign-in failed. Please try again.';
      });
    }
  }

  void _startCooldown() {
    _cooldownSeconds = 60;
    _cooldownTimer?.cancel();
    _cooldownTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (_cooldownSeconds <= 0) {
        timer.cancel();
      } else {
        setState(() => _cooldownSeconds--);
      }
    });
  }

  String _mapAuthError(String code) {
    switch (code) {
      case 'invalid-phone-number':
        return 'Invalid phone number. Please check and try again.';
      case 'too-many-requests':
        return 'Too many attempts. Please try again later.';
      case 'invalid-verification-code':
        return 'Incorrect OTP. Please check and try again.';
      case 'session-expired':
        return 'OTP has expired. Please request a new one.';
      case 'quota-exceeded':
        return 'SMS quota exceeded. Please try again later.';
      default:
        return 'An error occurred. Please try again.';
    }
  }

  @override
  void dispose() {
    _phoneController.dispose();
    _otpController.dispose();
    _cooldownTimer?.cancel();
    super.dispose();
  }
}
