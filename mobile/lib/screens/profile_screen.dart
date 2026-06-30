/// WardWatch - Profile Screen (Step 3.x)
/// Shows user profile, points, badges, and campaign history.
library;

import 'package:flutter/material.dart';
import '../services/api_service.dart';

class ProfileScreen extends StatefulWidget {
  const ProfileScreen({super.key});

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  Map<String, dynamic>? _profile;
  bool _isLoading = true;
  String _errorMessage = '';

  @override
  void initState() {
    super.initState();
    _fetchProfile();
  }

  Future<void> _fetchProfile() async {
    setState(() {
      _isLoading = true;
      _errorMessage = '';
    });
    try {
      final result = await apiService.get('/api/v1/users/me');
      setState(() {
        _profile = result;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _isLoading = false;
        _errorMessage = e is ApiException ? e.message : 'Failed to load profile.';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('My Profile'),
        backgroundColor: const Color(0xFF1565C0),
        foregroundColor: Colors.white,
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _fetchProfile,
          ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _errorMessage.isNotEmpty
              ? Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Text(_errorMessage),
                      const SizedBox(height: 12),
                      ElevatedButton(
                          onPressed: _fetchProfile, child: const Text('Retry')),
                    ],
                  ),
                )
              : _buildContent(),
    );
  }

  Widget _buildContent() {
    final p = _profile!;
    final badges = (p['badges'] as List<dynamic>?)?.cast<String>() ?? [];
    final campaigns = (p['campaigns'] as List<dynamic>?)
            ?.map((e) => e as Map<String, dynamic>)
            .toList() ??
        [];

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Avatar and name
          Center(
            child: Column(
              children: [
                CircleAvatar(
                  radius: 48,
                  backgroundColor: const Color(0xFF1565C0),
                  child: Text(
                    (p['display_name'] as String? ?? 'U')[0].toUpperCase(),
                    style: const TextStyle(
                        fontSize: 36,
                        color: Colors.white,
                        fontWeight: FontWeight.bold),
                  ),
                ),
                const SizedBox(height: 12),
                Text(
                  p['display_name'] as String? ?? 'Citizen',
                  style: const TextStyle(
                      fontSize: 22, fontWeight: FontWeight.bold),
                ),
                Text(
                  p['email'] as String? ?? '',
                  style: const TextStyle(color: Colors.black54),
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),

          // Stats row
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceAround,
            children: [
              _statCard('Points', '${p['points'] ?? 0}', Icons.star,
                  Colors.amber),
              _statCard('Campaigns', '${p['campaigns_created'] ?? 0}',
                  Icons.campaign, Colors.blue),
              _statCard('Resolved', '${p['campaigns_resolved'] ?? 0}',
                  Icons.check_circle, Colors.green),
            ],
          ),
          const SizedBox(height: 24),

          // Badges
          if (badges.isNotEmpty) ...[
            const Text('Badges',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: badges
                  .map((b) => Chip(
                        label: Text(b,
                            style: const TextStyle(fontSize: 12)),
                        backgroundColor: Colors.purple[50],
                        avatar: const Icon(Icons.emoji_events,
                            size: 16, color: Colors.purple),
                      ))
                  .toList(),
            ),
            const SizedBox(height: 24),
          ],

          // Campaign history
          if (campaigns.isNotEmpty) ...[
            const Text('My Campaigns',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
            const SizedBox(height: 8),
            ...campaigns.map((c) => Card(
                  margin: const EdgeInsets.only(bottom: 8),
                  child: ListTile(
                    leading: const Icon(Icons.campaign, color: Color(0xFF1565C0)),
                    title: Text(c['title'] as String? ?? ''),
                    subtitle: Text(c['status'] as String? ?? ''),
                    trailing: Text(
                      '${c['citizen_count'] ?? 0} citizens',
                      style: const TextStyle(fontSize: 12, color: Colors.black54),
                    ),
                  ),
                )),
          ],
        ],
      ),
    );
  }

  Widget _statCard(String label, String value, IconData icon, Color color) {
    return Column(
      children: [
        Icon(icon, color: color, size: 28),
        const SizedBox(height: 4),
        Text(value,
            style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold)),
        Text(label, style: const TextStyle(fontSize: 12, color: Colors.black54)),
      ],
    );
  }
}
