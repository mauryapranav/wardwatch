/// WardWatch - Onboarding Screen
/// Multi-step onboarding with age verification and DPDP consent.
library;

import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'auth_screen.dart';

class OnboardingScreen extends StatefulWidget {
  const OnboardingScreen({super.key});

  @override
  State<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends State<OnboardingScreen> {
  final PageController _pageController = PageController();
  int _currentPage = 0;

  // Age verification
  int? _selectedAge;
  String _ageCategory = '';

  // Consent checkboxes
  bool _consentIdentity = false;
  bool _consentLocation = false;
  bool _consentPhotos = false;
  bool _consentSharing = false;
  bool _consentLeaderboard = false; // Optional

  bool _isSubmitting = false;

  bool get _requiredConsentsGiven =>
      _consentIdentity && _consentLocation && _consentPhotos && _consentSharing;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Column(
          children: [
            // Progress indicator
            LinearProgressIndicator(
              value: (_currentPage + 1) / 3,
              backgroundColor: Colors.grey[200],
              valueColor: const AlwaysStoppedAnimation<Color>(Color(0xFF1565C0)),
            ),
            Expanded(
              child: PageView(
                controller: _pageController,
                physics: const NeverScrollableScrollPhysics(), // No skipping
                onPageChanged: (page) => setState(() => _currentPage = page),
                children: [
                  _buildWelcomePage(),
                  _buildAgeVerificationPage(),
                  _buildConsentPage(),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  // ─── Page 1: Welcome ────────────────────────────────────────────────────────
  Widget _buildWelcomePage() {
    return Padding(
      padding: const EdgeInsets.all(32.0),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(Icons.location_city, size: 80, color: Color(0xFF1565C0)),
          const SizedBox(height: 32),
          const Text(
            'WardWatch',
            style: TextStyle(fontSize: 36, fontWeight: FontWeight.bold, color: Color(0xFF1565C0)),
          ),
          const SizedBox(height: 16),
          const Text(
            'Civic accountability in your hands.\nReport issues, track progress, hold officials accountable.',
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 16, color: Colors.black54, height: 1.5),
          ),
          const SizedBox(height: 48),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton(
              onPressed: () => _pageController.nextPage(
                duration: const Duration(milliseconds: 300),
                curve: Curves.easeInOut,
              ),
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFF1565C0),
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(vertical: 16),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              ),
              child: const Text('Get Started', style: TextStyle(fontSize: 18)),
            ),
          ),
        ],
      ),
    );
  }

  // ─── Page 2: Age Verification ───────────────────────────────────────────────
  Widget _buildAgeVerificationPage() {
    if (_ageCategory == 'under_13') {
      return _buildParentalConsentScreen();
    }

    return Padding(
      padding: const EdgeInsets.all(32.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SizedBox(height: 32),
          const Text(
            'Age Verification',
            style: TextStyle(fontSize: 28, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 8),
          const Text(
            'Please enter your age to continue.',
            style: TextStyle(fontSize: 16, color: Colors.black54),
          ),
          const SizedBox(height: 32),
          // Age selection
          DropdownButtonFormField<int>(
            decoration: InputDecoration(
              labelText: 'Your Age',
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
            ),
            hint: const Text('Select your age'),
            items: List.generate(100, (i) => i + 1)
                .map((age) => DropdownMenuItem(value: age, child: Text('$age years')))
                .toList(),
            onChanged: (value) {
              setState(() {
                _selectedAge = value;
                if (value != null) {
                  if (value < 13) {
                    _ageCategory = 'under_13';
                  } else if (value < 18) {
                    _ageCategory = 'teen';
                  } else {
                    _ageCategory = 'adult';
                  }
                }
              });
            },
          ),
          if (_ageCategory == 'teen') ...[
            const SizedBox(height: 16),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.amber[50],
                border: Border.all(color: Colors.amber),
                borderRadius: BorderRadius.circular(8),
              ),
              child: const Row(
                children: [
                  Icon(Icons.info_outline, color: Colors.amber),
                  SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      'Note: Users under 18 cannot appear on the public leaderboard.',
                      style: TextStyle(fontSize: 13),
                    ),
                  ),
                ],
              ),
            ),
          ],
          const Spacer(),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton(
              onPressed: _selectedAge == null || _ageCategory == 'under_13'
                  ? null
                  : () => _pageController.nextPage(
                      duration: const Duration(milliseconds: 300),
                      curve: Curves.easeInOut,
                    ),
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFF1565C0),
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(vertical: 16),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              ),
              child: const Text('Continue', style: TextStyle(fontSize: 18)),
            ),
          ),
          const SizedBox(height: 16),
        ],
      ),
    );
  }

  Widget _buildParentalConsentScreen() {
    return Padding(
      padding: const EdgeInsets.all(32.0),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(Icons.family_restroom, size: 80, color: Colors.orange),
          const SizedBox(height: 32),
          const Text(
            'Parental Consent Required',
            style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 16),
          const Text(
            'WardWatch requires parental consent for users under 13.\nPlease contact us to register with parental consent.',
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 16, color: Colors.black54, height: 1.5),
          ),
          const SizedBox(height: 32),
          ElevatedButton.icon(
            onPressed: () {
              // Contact support (placeholder)
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(
                  content: Text('Please email support@wardwatch.app for parental consent registration.'),
                ),
              );
            },
            icon: const Icon(Icons.email_outlined),
            label: const Text('Contact Support'),
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.orange,
              foregroundColor: Colors.white,
              padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 32),
            ),
          ),
          const SizedBox(height: 16),
          TextButton(
            onPressed: () => setState(() {
              _ageCategory = '';
              _selectedAge = null;
            }),
            child: const Text('Change Age'),
          ),
        ],
      ),
    );
  }

  // ─── Page 3: Consent ───────────────────────────────────────────────────────
  Widget _buildConsentPage() {
    return Padding(
      padding: const EdgeInsets.all(24.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SizedBox(height: 16),
          const Text(
            'Privacy & Consent',
            style: TextStyle(fontSize: 28, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 4),
          const Text(
            'Please review and accept to continue. All items marked * are required.',
            style: TextStyle(fontSize: 14, color: Colors.black54),
          ),
          const SizedBox(height: 16),
          Expanded(
            child: SingleChildScrollView(
              child: Column(
                children: [
                  _buildConsentTile(
                    title: '* Identity',
                    description:
                        'We collect your name and phone number to identify you as a civic reporter.',
                    value: _consentIdentity,
                    onChanged: (v) => setState(() => _consentIdentity = v!),
                    required: true,
                  ),
                  _buildConsentTile(
                    title: '* Location',
                    description:
                        'We capture GPS coordinates (ward-level precision) to route complaints to the correct authorities.',
                    value: _consentLocation,
                    onChanged: (v) => setState(() => _consentLocation = v!),
                    required: true,
                  ),
                  _buildConsentTile(
                    title: '* Photos',
                    description:
                        'We store photos of civic issues. EXIF location data is stripped before storage.',
                    value: _consentPhotos,
                    onChanged: (v) => setState(() => _consentPhotos = v!),
                    required: true,
                  ),
                  _buildConsentTile(
                    title: '* Sharing',
                    description:
                        'Your name and complaint details are shared with municipal officials for processing.',
                    value: _consentSharing,
                    onChanged: (v) => setState(() => _consentSharing = v!),
                    required: true,
                  ),
                  _buildConsentTile(
                    title: 'Leaderboard (Optional)',
                    description:
                        'Your civic reputation score may appear on the public leaderboard.',
                    value: _consentLeaderboard,
                    onChanged: (v) => setState(() => _consentLeaderboard = v!),
                    required: false,
                  ),
                  const SizedBox(height: 8),
                  RichText(
                    text: TextSpan(
                      style: const TextStyle(color: Colors.black54, fontSize: 13),
                      children: [
                        const TextSpan(text: 'By continuing, you agree to our '),
                        TextSpan(
                          text: 'Privacy Policy',
                          style: const TextStyle(
                            color: Color(0xFF1565C0),
                            decoration: TextDecoration.underline,
                          ),
                          recognizer: TapGestureRecognizer()
                            ..onTap = () {
                              // Privacy policy URL placeholder
                              ScaffoldMessenger.of(context).showSnackBar(
                                const SnackBar(
                                  content: Text('Privacy Policy: https://wardwatch.app/privacy'),
                                ),
                              );
                            },
                        ),
                        const TextSpan(text: '.'),
                      ],
                    ),
                  ),
                  const SizedBox(height: 16),
                ],
              ),
            ),
          ),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton(
              onPressed: _requiredConsentsGiven && !_isSubmitting ? _submitConsent : null,
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFF1565C0),
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(vertical: 16),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              ),
              child: _isSubmitting
                  ? const SizedBox(
                      height: 20,
                      width: 20,
                      child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2),
                    )
                  : const Text('I Agree & Continue', style: TextStyle(fontSize: 18)),
            ),
          ),
          const SizedBox(height: 16),
        ],
      ),
    );
  }

  Widget _buildConsentTile({
    required String title,
    required String description,
    required bool value,
    required ValueChanged<bool?> onChanged,
    required bool required,
  }) {
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: CheckboxListTile(
        value: value,
        onChanged: onChanged,
        controlAffinity: ListTileControlAffinity.leading,
        title: Text(
          title,
          style: TextStyle(
            fontWeight: FontWeight.w600,
            color: required ? Colors.black87 : Colors.black54,
          ),
        ),
        subtitle: Text(description, style: const TextStyle(fontSize: 13)),
      ),
    );
  }

  Future<void> _submitConsent() async {
    setState(() => _isSubmitting = true);

    try {
      // Sign in anonymously first (consent requires a user ID)
      if (FirebaseAuth.instance.currentUser == null) {
        await FirebaseAuth.instance.signInAnonymously();
      }
      final uid = FirebaseAuth.instance.currentUser!.uid;

      // Store consent record in Firestore
      await FirebaseFirestore.instance.collection('consent').doc(uid).set({
        'identity': _consentIdentity,
        'location': _consentLocation,
        'photos': _consentPhotos,
        'sharing': _consentSharing,
        'leaderboard': _consentLeaderboard,
        'consented_at': FieldValue.serverTimestamp(),
        'version': '1.0',
        'age_category': _ageCategory,
      });

      // Store age_category in user profile
      await FirebaseFirestore.instance.collection('users').doc(uid).set({
        'age_category': _ageCategory,
        'leaderboard_consent': _consentLeaderboard,
      }, SetOptions(merge: true));

      if (!mounted) return;

      // Navigate to auth screen
      Navigator.of(context).pushReplacement(
        MaterialPageRoute(builder: (_) => const AuthScreen()),
      );
    } catch (e) {
      setState(() => _isSubmitting = false);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Failed to save consent. Please check your connection and try again.'),
          backgroundColor: Colors.red,
        ),
      );
    }
  }

  @override
  void dispose() {
    _pageController.dispose();
    super.dispose();
  }
}
