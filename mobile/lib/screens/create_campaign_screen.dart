/// WardWatch - Create Campaign Screen (Step 1.12)
library;

import 'package:flutter/material.dart';
import '../services/api_service.dart';
import 'campaign_detail_screen.dart';
import 'join_campaign_screen.dart';

class CreateCampaignScreen extends StatefulWidget {
  final String storagePath;
  final String photoId;
  final double gpsLat;
  final double gpsLng;
  final String address;

  const CreateCampaignScreen({
    super.key,
    required this.storagePath,
    required this.photoId,
    required this.gpsLat,
    required this.gpsLng,
    required this.address,
  });

  @override
  State<CreateCampaignScreen> createState() => _CreateCampaignScreenState();
}

class _CreateCampaignScreenState extends State<CreateCampaignScreen> {
  // AI classification state
  Map<String, dynamic>? _classification;
  bool _isClassifying = true;
  bool _aiConfirmed = false;
  String _classificationError = '';

  // Manual override
  String _selectedType = 'other';
  int _selectedSeverity = 3;

  // Form
  final _titleController = TextEditingController();
  final _descController = TextEditingController();
  final _formKey = GlobalKey<FormState>();

  bool _isSubmitting = false;

  static const _issueTypes = [
    'pothole', 'streetlight', 'water', 'garbage', 'sidewalk', 'other',
  ];

  @override
  void initState() {
    super.initState();
    _classifyPhoto();
  }

  Future<void> _classifyPhoto() async {
    setState(() {
      _isClassifying = true;
      _classificationError = '';
    });

    try {
      final result = await apiService.post(
        '/api/v1/ai/classify',
        body: {'storage_path': widget.storagePath},
      );
      setState(() {
        _classification = result;
        _selectedType = result['type'] as String? ?? 'other';
        _selectedSeverity = (result['severity'] as num?)?.toInt() ?? 3;
        _isClassifying = false;
      });
    } catch (e) {
      setState(() {
        _isClassifying = false;
        _classificationError = 'AI classification unavailable. Please select manually.';
      });
    }
  }

  Future<void> _submitCampaign() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() => _isSubmitting = true);

    try {
      final result = await apiService.post('/api/v1/issues', body: {
        'title': _titleController.text.trim(),
        'description': _descController.text.trim(),
        'issue_type': _selectedType,
        'severity': _selectedSeverity,
        'location': {'lat': widget.gpsLat, 'lng': widget.gpsLng},
        'address': widget.address,
        'storage_path': widget.storagePath,
        'photo_id': widget.photoId,
      });

      if (!mounted) return;

      final status = result['status'] as String?;
      final campaignId = result['campaign_id'] as String?;

      if (status == 'DUPLICATE_FOUND' && campaignId != null) {
        // Show join existing campaign screen
        Navigator.of(context).pushReplacement(
          MaterialPageRoute(
            builder: (_) => JoinCampaignScreen(
              highlightCampaignId: campaignId,
              message: 'A similar issue has already been reported nearby. Join the existing campaign?',
            ),
          ),
        );
      } else if (campaignId != null) {
        // Success: navigate to campaign detail
        Navigator.of(context).pushReplacement(
          MaterialPageRoute(
            builder: (_) => CampaignDetailScreen(campaignId: campaignId),
          ),
        );
      }
    } catch (e) {
      setState(() => _isSubmitting = false);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            e is ApiException ? e.message : 'Failed to create campaign. Please try again.',
          ),
          backgroundColor: Colors.red,
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Report Issue'),
        backgroundColor: const Color(0xFF1565C0),
        foregroundColor: Colors.white,
      ),
      body: _isClassifying
          ? const Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  CircularProgressIndicator(),
                  SizedBox(height: 16),
                  Text('AI is analyzing your photo...'),
                ],
              ),
            )
          : Form(
              key: _formKey,
              child: SingleChildScrollView(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // AI Classification Result
                    if (_classification != null && !_aiConfirmed)
                      _buildAIResultCard(),
                    if (_aiConfirmed || _classification == null)
                      _buildManualSelectionCard(),

                    const SizedBox(height: 16),

                    // Title
                    TextFormField(
                      controller: _titleController,
                      maxLength: 200,
                      decoration: InputDecoration(
                        labelText: 'Title *',
                        hintText: 'e.g., Large pothole on Main Road',
                        border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                      ),
                      validator: (v) =>
                          v == null || v.trim().isEmpty ? 'Title is required' : null,
                    ),

                    const SizedBox(height: 12),

                    // Description
                    TextFormField(
                      controller: _descController,
                      maxLength: 500,
                      maxLines: 4,
                      decoration: InputDecoration(
                        labelText: 'Description *',
                        hintText: 'Describe the issue in detail...',
                        border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                        alignLabelWithHint: true,
                      ),
                      validator: (v) =>
                          v == null || v.trim().isEmpty ? 'Description is required' : null,
                    ),

                    const SizedBox(height: 12),

                    // Address
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: Colors.grey[100],
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: Colors.grey[300]!),
                      ),
                      child: Row(
                        children: [
                          const Icon(Icons.location_on, color: Color(0xFF1565C0)),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(widget.address,
                                style: const TextStyle(fontSize: 14)),
                          ),
                        ],
                      ),
                    ),

                    const SizedBox(height: 24),

                    SizedBox(
                      width: double.infinity,
                      child: ElevatedButton(
                        onPressed: _isSubmitting ? null : _submitCampaign,
                        style: ElevatedButton.styleFrom(
                          backgroundColor: const Color(0xFF1565C0),
                          foregroundColor: Colors.white,
                          padding: const EdgeInsets.symmetric(vertical: 16),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(12),
                          ),
                        ),
                        child: _isSubmitting
                            ? const SizedBox(
                                height: 20,
                                width: 20,
                                child: CircularProgressIndicator(
                                  color: Colors.white,
                                  strokeWidth: 2,
                                ),
                              )
                            : const Text('Submit Report',
                                style: TextStyle(fontSize: 18)),
                      ),
                    ),
                    const SizedBox(height: 24),
                  ],
                ),
              ),
            ),
    );
  }

  Widget _buildAIResultCard() {
    final type = _classification!['type'] as String? ?? 'other';
    final severity = (_classification!['severity'] as num?)?.toInt() ?? 3;
    final confidence = (_classification!['confidence'] as num?)?.toDouble() ?? 0.5;
    final description = _classification!['description'] as String? ?? '';

    return Card(
      margin: const EdgeInsets.only(bottom: 16),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Row(
              children: [
                Icon(Icons.auto_awesome, color: Colors.purple),
                SizedBox(width: 8),
                Text('AI Classification',
                    style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
              ],
            ),
            const SizedBox(height: 12),
            Text('Type: ${type.toUpperCase()}',
                style: const TextStyle(fontSize: 15)),
            Text('Severity: $severity / 5',
                style: const TextStyle(fontSize: 15)),
            Text('Confidence: ${(confidence * 100).toStringAsFixed(0)}%',
                style: TextStyle(
                  fontSize: 13,
                  color: confidence >= 0.7 ? Colors.green : Colors.orange,
                )),
            if (description.isNotEmpty)
              Padding(
                padding: const EdgeInsets.only(top: 4),
                child: Text(description,
                    style: const TextStyle(fontSize: 13, color: Colors.black54)),
              ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton(
                    onPressed: () => setState(() => _aiConfirmed = true),
                    child: const Text('Not correct — Edit manually'),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: ElevatedButton(
                    onPressed: () => setState(() => _aiConfirmed = false),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.green,
                      foregroundColor: Colors.white,
                    ),
                    child: const Text('Yes, Correct!'),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildManualSelectionCard() {
    return Card(
      margin: const EdgeInsets.only(bottom: 16),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (_classificationError.isNotEmpty)
              Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: Text(_classificationError,
                    style: const TextStyle(color: Colors.orange, fontSize: 13)),
              ),
            const Text('Issue Type',
                style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15)),
            const SizedBox(height: 8),
            DropdownButtonFormField<String>(
              value: _selectedType,
              decoration: InputDecoration(
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
              ),
              items: _issueTypes
                  .map((t) => DropdownMenuItem(
                      value: t,
                      child: Text(t[0].toUpperCase() + t.substring(1))))
                  .toList(),
              onChanged: (v) => setState(() => _selectedType = v!),
            ),
            const SizedBox(height: 16),
            Text('Severity: $_selectedSeverity / 5',
                style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15)),
            Slider(
              value: _selectedSeverity.toDouble(),
              min: 1,
              max: 5,
              divisions: 4,
              label: '$_selectedSeverity',
              onChanged: (v) => setState(() => _selectedSeverity = v.toInt()),
              activeColor: const Color(0xFF1565C0),
            ),
          ],
        ),
      ),
    );
  }

  @override
  void dispose() {
    _titleController.dispose();
    _descController.dispose();
    super.dispose();
  }
}
