import 'dart:async';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:camera/camera.dart';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import '../services/api_service.dart';

/// WardWatch - Verification Screen (Step 4.5)
///
/// Receives campaign_id from navigation.
/// Shows campaign details with original photo.
/// If status is 'verifying': shows 72-hour countdown + submit button.
/// Camera capture → upload with type='verification' → confirmation.
/// Handles: already verified, window expired (show result).
class VerificationScreen extends StatefulWidget {
  final String campaignId;

  const VerificationScreen({super.key, required this.campaignId});

  @override
  State<VerificationScreen> createState() => _VerificationScreenState();
}

class _VerificationScreenState extends State<VerificationScreen> {
  // Campaign data
  Map<String, dynamic>? _campaign;
  bool _isLoading = true;
  String? _errorMessage;

  // Verification state
  bool _hasAlreadyVerified = false;
  bool _isSubmitting = false;
  bool _submitted = false;
  String? _submitError;

  // Camera
  CameraController? _cameraController;
  XFile? _capturedPhoto;
  bool _showCamera = false;
  bool _showPreview = false;

  // 72-hour countdown
  Timer? _countdownTimer;
  Duration? _timeRemaining;
  bool _windowExpired = false;

  // Verification stats
  int _verificationCount = 0;
  double _approvalRate = 0.0;

  @override
  void initState() {
    super.initState();
    _loadCampaign();
  }

  @override
  void dispose() {
    _cameraController?.dispose();
    _countdownTimer?.cancel();
    super.dispose();
  }

  Future<void> _loadCampaign() async {
    setState(() { _isLoading = true; _errorMessage = null; });
    try {
      final apiService = ApiService();
      final campaign = await apiService.getCampaignById(widget.campaignId);
      final uid = FirebaseAuth.instance.currentUser?.uid ?? '';

      // Check if user already verified
      final photosSnap = await FirebaseFirestore.instance
          .collection('photos')
          .where('campaign_id', isEqualTo: widget.campaignId)
          .where('type', isEqualTo: 'verification')
          .where('uploader_id', isEqualTo: uid)
          .limit(1)
          .get();
      final alreadyVerified = photosSnap.docs.isNotEmpty;

      // Count all verification photos
      final allVerifications = await FirebaseFirestore.instance
          .collection('photos')
          .where('campaign_id', isEqualTo: widget.campaignId)
          .where('type', isEqualTo: 'verification')
          .get();

      setState(() {
        _campaign = campaign;
        _hasAlreadyVerified = alreadyVerified;
        _verificationCount = allVerifications.docs.length;
        _approvalRate = (campaign['approval_rate'] as num?)?.toDouble() ?? 0.0;
        _isLoading = false;
      });

      // Start 72h countdown if in verifying status
      if (campaign['status'] == 'verifying') {
        _startCountdown(campaign);
      } else if (campaign['status'] == 'closed' || campaign['status'] == 'reopened') {
        _windowExpired = true;
      }
    } catch (e) {
      setState(() {
        _isLoading = false;
        _errorMessage = 'Failed to load campaign. Please try again.';
      });
    }
  }

  void _startCountdown(Map<String, dynamic> campaign) {
    // Find when status changed to 'verifying' from timeline
    final timeline = (campaign['timeline'] as List?)?.cast<Map<String, dynamic>>() ?? [];
    DateTime? verifySince;
    for (final event in timeline.reversed) {
      if (event['action'] == 'status_updated') {
        try {
          verifySince = DateTime.parse(event['timestamp'] as String);
          break;
        } catch (_) {}
      }
    }
    verifySince ??= DateTime.now().subtract(const Duration(hours: 1));

    final windowEnd = verifySince.add(const Duration(hours: 72));

    _countdownTimer = Timer.periodic(const Duration(seconds: 60), (_) {
      final remaining = windowEnd.difference(DateTime.now());
      if (remaining.isNegative) {
        _countdownTimer?.cancel();
        setState(() { _windowExpired = true; });
      } else {
        setState(() { _timeRemaining = remaining; });
      }
    });

    // Initial update
    final remaining = windowEnd.difference(DateTime.now());
    if (remaining.isNegative) {
      setState(() { _windowExpired = true; });
    } else {
      setState(() { _timeRemaining = remaining; });
    }
  }

  Future<void> _openCamera() async {
    try {
      final cameras = await availableCameras();
      if (cameras.isEmpty) throw Exception('No camera available');
      final camera = cameras.first;
      _cameraController = CameraController(camera, ResolutionPreset.high);
      await _cameraController!.initialize();
      setState(() { _showCamera = true; });
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Camera access failed. Please check permissions.')),
      );
    }
  }

  Future<void> _capturePhoto() async {
    try {
      final photo = await _cameraController?.takePicture();
      if (photo != null) {
        setState(() {
          _capturedPhoto = photo;
          _showCamera = false;
          _showPreview = true;
        });
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Failed to capture photo. Please try again.')),
      );
    }
  }

  Future<void> _submitVerification() async {
    if (_capturedPhoto == null) return;
    setState(() { _isSubmitting = true; _submitError = null; });

    try {
      final apiService = ApiService();
      // Upload photo with type='verification' parameter
      final uploadResult = await apiService.uploadPhoto(
        File(_capturedPhoto!.path),
        campaignId: widget.campaignId,
        photoType: 'verification',
      );

      // Temp file cleanup
      try { File(_capturedPhoto!.path).deleteSync(); } catch (_) {}

      setState(() {
        _isSubmitting = false;
        _submitted = true;
        _showPreview = false;
        _capturedPhoto = null;
        _hasAlreadyVerified = true;
        _verificationCount++;
      });
    } catch (e) {
      setState(() {
        _isSubmitting = false;
        _submitError = 'Failed to submit verification. Please try again.';
      });
    }
  }

  String _formatCountdown(Duration d) {
    final days = d.inDays;
    final hours = d.inHours.remainder(24);
    final mins = d.inMinutes.remainder(60);
    if (days > 0) return '$days days, $hours hours remaining';
    return '$hours hours, $mins minutes remaining';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0f0f1a),
      appBar: AppBar(
        backgroundColor: const Color(0xFF1a1a2e),
        title: const Text('Verify Resolution', style: TextStyle(color: Colors.white)),
        iconTheme: const IconThemeData(color: Colors.white),
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator(color: Color(0xFFe94560)))
          : _errorMessage != null
              ? _buildError()
              : _showCamera
                  ? _buildCameraView()
                  : _showPreview
                      ? _buildPreview()
                      : _buildMainView(),
    );
  }

  Widget _buildError() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(Icons.error_outline, color: Color(0xFFe94560), size: 48),
          const SizedBox(height: 16),
          Text(_errorMessage!, style: const TextStyle(color: Colors.white70)),
          const SizedBox(height: 20),
          ElevatedButton(
            onPressed: _loadCampaign,
            style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFFe94560)),
            child: const Text('Retry'),
          ),
        ],
      ),
    );
  }

  Widget _buildMainView() {
    final campaign = _campaign!;
    final status = campaign['status'] as String? ?? '';

    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Campaign card
          _buildCampaignCard(campaign),
          const SizedBox(height: 24),

          // Status-based content
          if (status == 'verifying' && !_windowExpired) ...[
            _buildCountdownCard(),
            const SizedBox(height: 24),
            _buildVerificationStats(),
            const SizedBox(height: 24),
            _buildVerificationAction(),
          ] else if (_windowExpired || status == 'closed' || status == 'reopened') ...[
            _buildResultCard(status),
          ] else ...[
            _buildNotVerifyingCard(status),
          ],
        ],
      ),
    );
  }

  Widget _buildCampaignCard(Map<String, dynamic> campaign) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.05),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.white.withOpacity(0.1)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              _issueTypeBadge(campaign['issue_type'] ?? 'other'),
              const SizedBox(width: 8),
              _statusBadge(campaign['status'] ?? ''),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            campaign['title'] ?? 'Campaign',
            style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 6),
          Text(
            '📍 ${campaign['address'] ?? 'Unknown location'}',
            style: const TextStyle(color: Colors.white54, fontSize: 13),
          ),
          const SizedBox(height: 10),
          Row(
            children: [
              const Icon(Icons.people, color: Colors.white38, size: 16),
              const SizedBox(width: 6),
              Text('${campaign['citizen_count'] ?? 0} citizens', style: const TextStyle(color: Colors.white54, fontSize: 13)),
            ],
          ),
          const SizedBox(height: 12),
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: Colors.amber.withOpacity(0.08),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: Colors.amber.withOpacity(0.3)),
            ),
            child: const Row(
              children: [
                Icon(Icons.shield_outlined, color: Colors.amber, size: 16),
                SizedBox(width: 8),
                Expanded(
                  child: Text(
                    'EXIF metadata (GPS location) has been stripped from all photos before storage.',
                    style: TextStyle(color: Colors.amber, fontSize: 11),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildCountdownCard() {
    final remaining = _timeRemaining;
    if (remaining == null) return const SizedBox.shrink();

    final isUrgent = remaining.inHours < 24;
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: isUrgent ? Colors.red.withOpacity(0.08) : Colors.blue.withOpacity(0.08),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: isUrgent ? Colors.red.withOpacity(0.3) : Colors.blue.withOpacity(0.3)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.timer, color: isUrgent ? Colors.red : Colors.blue, size: 20),
              const SizedBox(width: 8),
              Text(
                '72-Hour Verification Window',
                style: TextStyle(
                  color: isUrgent ? Colors.red : Colors.blue,
                  fontWeight: FontWeight.bold,
                  fontSize: 14,
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Text(
            _formatCountdown(remaining),
            style: TextStyle(
              color: isUrgent ? Colors.red[300] : Colors.blue[300],
              fontSize: 16,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 6),
          const Text(
            'The official has marked this issue as resolved. Please verify by submitting a photo of the current state.',
            style: TextStyle(color: Colors.white54, fontSize: 12),
          ),
        ],
      ),
    );
  }

  Widget _buildVerificationStats() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.04),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.white.withOpacity(0.08)),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceAround,
        children: [
          _statItem('Verifications', _verificationCount.toString(), Icons.how_to_vote),
          _statItem('Approval Rate', '${(_approvalRate * 100).toStringAsFixed(0)}%', Icons.thumb_up),
          _statItem('Required', '60%', Icons.check_circle),
        ],
      ),
    );
  }

  Widget _statItem(String label, String value, IconData icon) {
    return Column(
      children: [
        Icon(icon, color: const Color(0xFFe94560), size: 22),
        const SizedBox(height: 6),
        Text(value, style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold)),
        Text(label, style: const TextStyle(color: Colors.white54, fontSize: 11)),
      ],
    );
  }

  Widget _buildVerificationAction() {
    if (_submitted) {
      return Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: Colors.green.withOpacity(0.1),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: Colors.green.withOpacity(0.3)),
        ),
        child: const Column(
          children: [
            Icon(Icons.check_circle, color: Colors.green, size: 48),
            SizedBox(height: 12),
            Text('Thank you for verifying!', style: TextStyle(color: Colors.green, fontSize: 18, fontWeight: FontWeight.bold)),
            SizedBox(height: 6),
            Text('Your vote has been recorded.', style: TextStyle(color: Colors.white54)),
          ],
        ),
      );
    }

    if (_hasAlreadyVerified) {
      return Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: Colors.white.withOpacity(0.04),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: Colors.white.withOpacity(0.1)),
        ),
        child: const Column(
          children: [
            Icon(Icons.how_to_reg, color: Colors.white38, size: 40),
            SizedBox(height: 10),
            Text('You have already verified this campaign.', style: TextStyle(color: Colors.white70), textAlign: TextAlign.center),
          ],
        ),
      );
    }

    return ElevatedButton.icon(
      onPressed: _openCamera,
      icon: const Icon(Icons.camera_alt),
      label: const Text('Submit Verification Photo', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
      style: ElevatedButton.styleFrom(
        backgroundColor: const Color(0xFFe94560),
        foregroundColor: Colors.white,
        minimumSize: const Size(double.infinity, 54),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      ),
    );
  }

  Widget _buildResultCard(String status) {
    final isClosed = status == 'closed';
    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: isClosed ? Colors.green.withOpacity(0.08) : Colors.orange.withOpacity(0.08),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: isClosed ? Colors.green.withOpacity(0.3) : Colors.orange.withOpacity(0.3)),
      ),
      child: Column(
        children: [
          Icon(
            isClosed ? Icons.verified : Icons.replay,
            color: isClosed ? Colors.green : Colors.orange,
            size: 48,
          ),
          const SizedBox(height: 12),
          Text(
            'Verification Window Closed',
            style: TextStyle(color: isClosed ? Colors.green : Colors.orange, fontSize: 16, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 8),
          Text(
            isClosed
                ? 'Result: ✅ Campaign Closed\nApproval rate: ${(_approvalRate * 100).toStringAsFixed(0)}%'
                : 'Result: ⚠️ Campaign Reopened\nApproval rate: ${(_approvalRate * 100).toStringAsFixed(0)}% (< 60% required)',
            style: const TextStyle(color: Colors.white70, fontSize: 13),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }

  Widget _buildNotVerifyingCard(String status) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.04),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.white.withOpacity(0.08)),
      ),
      child: Column(
        children: [
          const Icon(Icons.info_outline, color: Colors.white38, size: 40),
          const SizedBox(height: 12),
          Text(
            'Campaign status: ${status.replaceAll('_', ' ')}',
            style: const TextStyle(color: Colors.white70, fontSize: 14),
          ),
          const SizedBox(height: 6),
          const Text(
            'Verification is only available when the official marks the campaign as resolved.',
            style: TextStyle(color: Colors.white38, fontSize: 12),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }

  Widget _buildCameraView() {
    if (_cameraController == null || !_cameraController!.value.isInitialized) {
      return const Center(child: CircularProgressIndicator(color: Color(0xFFe94560)));
    }
    return Stack(
      fit: StackFit.expand,
      children: [
        CameraPreview(_cameraController!),
        Positioned(
          bottom: 40,
          left: 0, right: 0,
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
            children: [
              IconButton(
                onPressed: () => setState(() { _showCamera = false; }),
                icon: const Icon(Icons.close, color: Colors.white, size: 32),
              ),
              GestureDetector(
                onTap: _capturePhoto,
                child: Container(
                  width: 72, height: 72,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    border: Border.all(color: Colors.white, width: 4),
                    color: Colors.white.withOpacity(0.3),
                  ),
                  child: const Icon(Icons.camera, color: Colors.white, size: 36),
                ),
              ),
              const SizedBox(width: 48),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildPreview() {
    return Column(
      children: [
        Expanded(
          child: Image.file(
            File(_capturedPhoto!.path),
            fit: BoxFit.cover,
            width: double.infinity,
          ),
        ),
        if (_submitError != null)
          Padding(
            padding: const EdgeInsets.all(12),
            child: Text(_submitError!, style: const TextStyle(color: Color(0xFFe94560))),
          ),
        Padding(
          padding: const EdgeInsets.all(20),
          child: Row(
            children: [
              Expanded(
                child: OutlinedButton(
                  onPressed: () => setState(() { _showPreview = false; _capturedPhoto = null; }),
                  style: OutlinedButton.styleFrom(
                    side: const BorderSide(color: Colors.white38),
                    foregroundColor: Colors.white,
                    minimumSize: const Size(0, 50),
                  ),
                  child: const Text('Retake'),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                flex: 2,
                child: ElevatedButton(
                  onPressed: _isSubmitting ? null : _submitVerification,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFFe94560),
                    foregroundColor: Colors.white,
                    minimumSize: const Size(0, 50),
                  ),
                  child: _isSubmitting
                      ? const CircularProgressIndicator(color: Colors.white, strokeWidth: 2)
                      : const Text('Submit Verification', fontWeight: FontWeight.w600),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _issueTypeBadge(String type) {
    final colors = <String, Color>{
      'pothole': Colors.red, 'streetlight': Colors.amber,
      'water': Colors.blue, 'garbage': Colors.green,
      'sidewalk': Colors.orange, 'other': Colors.grey,
    };
    final color = colors[type] ?? Colors.grey;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: color.withOpacity(0.2),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withOpacity(0.4)),
      ),
      child: Text(type, style: TextStyle(color: color, fontSize: 11, fontWeight: FontWeight.bold)),
    );
  }

  Widget _statusBadge(String status) {
    Color color;
    switch (status) {
      case 'verifying': color = Colors.purple; break;
      case 'closed': color = Colors.green; break;
      case 'reopened': color = Colors.orange; break;
      default: color = Colors.grey;
    }
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: color.withOpacity(0.2),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withOpacity(0.4)),
      ),
      child: Text(status.toUpperCase(), style: TextStyle(color: color, fontSize: 10, fontWeight: FontWeight.bold, letterSpacing: 0.5)),
    );
  }
}
