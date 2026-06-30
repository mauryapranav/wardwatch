/// WardWatch - Leaderboard Screen (Step 3.x)
/// Shows top citizens ranked by points.
library;

import 'package:flutter/material.dart';
import '../services/api_service.dart';

class LeaderboardScreen extends StatefulWidget {
  const LeaderboardScreen({super.key});

  @override
  State<LeaderboardScreen> createState() => _LeaderboardScreenState();
}

class _LeaderboardScreenState extends State<LeaderboardScreen> {
  List<Map<String, dynamic>> _entries = [];
  bool _isLoading = true;
  String _errorMessage = '';
  String _selectedScope = 'ward'; // ward | city | national

  @override
  void initState() {
    super.initState();
    _fetchLeaderboard();
  }

  Future<void> _fetchLeaderboard() async {
    setState(() {
      _isLoading = true;
      _errorMessage = '';
    });
    try {
      final result = await apiService.get(
        '/api/v1/leaderboard',
        queryParams: {'scope': _selectedScope},
      );
      final items = result['items'] as List<dynamic>? ?? [];
      setState(() {
        _entries = items.map((e) => e as Map<String, dynamic>).toList();
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _isLoading = false;
        _errorMessage = e is ApiException ? e.message : 'Failed to load leaderboard.';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Leaderboard'),
        backgroundColor: const Color(0xFF1565C0),
        foregroundColor: Colors.white,
      ),
      body: Column(
        children: [
          // Scope selector
          Padding(
            padding: const EdgeInsets.all(12),
            child: SegmentedButton<String>(
              segments: const [
                ButtonSegment(value: 'ward', label: Text('Ward')),
                ButtonSegment(value: 'city', label: Text('City')),
                ButtonSegment(value: 'national', label: Text('National')),
              ],
              selected: {_selectedScope},
              onSelectionChanged: (s) {
                setState(() => _selectedScope = s.first);
                _fetchLeaderboard();
              },
            ),
          ),

          // List
          Expanded(
            child: _isLoading
                ? const Center(child: CircularProgressIndicator())
                : _errorMessage.isNotEmpty
                    ? Center(
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Text(_errorMessage),
                            const SizedBox(height: 12),
                            ElevatedButton(
                              onPressed: _fetchLeaderboard,
                              child: const Text('Retry'),
                            ),
                          ],
                        ),
                      )
                    : _entries.isEmpty
                        ? const Center(child: Text('No leaderboard data yet.'))
                        : ListView.builder(
                            itemCount: _entries.length,
                            itemBuilder: (_, i) {
                              final entry = _entries[i];
                              final rank = i + 1;
                              return ListTile(
                                leading: _rankBadge(rank),
                                title: Text(entry['display_name'] as String? ?? 'Citizen'),
                                subtitle: Text('${entry['campaigns_created'] ?? 0} campaigns'),
                                trailing: Text(
                                  '${entry['points'] ?? 0} pts',
                                  style: const TextStyle(
                                    fontWeight: FontWeight.bold,
                                    fontSize: 16,
                                    color: Color(0xFF1565C0),
                                  ),
                                ),
                              );
                            },
                          ),
          ),
        ],
      ),
    );
  }

  Widget _rankBadge(int rank) {
    if (rank == 1) {
      return const CircleAvatar(
        backgroundColor: Colors.amber,
        child: Text('🥇', style: TextStyle(fontSize: 18)),
      );
    } else if (rank == 2) {
      return const CircleAvatar(
        backgroundColor: Colors.grey,
        child: Text('🥈', style: TextStyle(fontSize: 18)),
      );
    } else if (rank == 3) {
      return CircleAvatar(
        backgroundColor: Colors.brown[300],
        child: const Text('🥉', style: TextStyle(fontSize: 18)),
      );
    }
    return CircleAvatar(
      backgroundColor: Colors.blue[50],
      child: Text('$rank', style: const TextStyle(fontWeight: FontWeight.bold)),
    );
  }
}
