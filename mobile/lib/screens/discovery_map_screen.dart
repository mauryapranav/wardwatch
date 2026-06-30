/// WardWatch - Discovery Map Screen (Step 1.13)
/// Shows nearby campaigns on Google Maps.
/// Maps API key is in AndroidManifest.xml/AppDelegate.swift (restricted).
/// Geocoding uses backend proxy only.
library;

import 'package:flutter/material.dart';
import 'package:google_maps_flutter/google_maps_flutter.dart';
import 'package:geolocator/geolocator.dart';
import '../services/api_service.dart';
import 'camera_screen.dart';
import 'campaign_detail_screen.dart';
import 'leaderboard_screen.dart';
import 'profile_screen.dart';

// Issue type to map marker color
const _issueTypeHues = {
  'pothole': BitmapDescriptor.hueRed,
  'streetlight': BitmapDescriptor.hueYellow,
  'water': BitmapDescriptor.hueBlue,
  'garbage': BitmapDescriptor.hueGreen,
  'sidewalk': BitmapDescriptor.hueOrange,
  'other': BitmapDescriptor.hueViolet,
};

class DiscoveryMapScreen extends StatefulWidget {
  const DiscoveryMapScreen({super.key});

  @override
  State<DiscoveryMapScreen> createState() => _DiscoveryMapScreenState();
}

class _DiscoveryMapScreenState extends State<DiscoveryMapScreen> {
  GoogleMapController? _mapController;
  Position? _userLocation;
  Set<Marker> _markers = {};
  List<Map<String, dynamic>> _campaigns = [];
  bool _isLoading = true;
  String _errorMessage = '';
  int _selectedNavIndex = 0;
  Map<String, dynamic>? _selectedCampaign;

  @override
  void initState() {
    super.initState();
    _initLocation();
  }

  Future<void> _initLocation() async {
    try {
      // Check permission
      LocationPermission permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied) {
        permission = await Geolocator.requestPermission();
      }
      if (permission == LocationPermission.deniedForever) {
        setState(() {
          _isLoading = false;
          _errorMessage = 'Location permission denied. Enable in settings to see nearby issues.';
        });
        return;
      }

      final position = await Geolocator.getCurrentPosition(
        desiredAccuracy: LocationAccuracy.high,
      );

      setState(() => _userLocation = position);
      await _fetchNearbyCampaigns(position.latitude, position.longitude);
    } catch (e) {
      setState(() {
        _isLoading = false;
        _errorMessage = 'Could not get location. Please check location settings.';
      });
    }
  }

  Future<void> _fetchNearbyCampaigns(double lat, double lng) async {
    setState(() {
      _isLoading = true;
      _errorMessage = '';
    });

    try {
      final result = await apiService.get(
        '/api/v1/issues/nearby',
        queryParams: {
          'lat': lat.toString(),
          'lng': lng.toString(),
          'radius': '5000',
        },
      );

      // If result is a list directly (not wrapped)
      final List<Map<String, dynamic>> campaignList;
      if (result is List) {
        campaignList = (result as List).map((e) => e as Map<String, dynamic>).toList();
      } else if (result.containsKey('items')) {
        campaignList = (result['items'] as List<dynamic>)
            .map((e) => e as Map<String, dynamic>)
            .toList();
      } else if (result.containsKey('campaign_id')) {
        campaignList = [result];
      } else {
        campaignList = [];
      }

      final markers = <Marker>{};
      for (final campaign in campaignList) {
        final location = campaign['location'] as Map<String, dynamic>?;
        if (location == null) continue;

        final markerLat = (location['lat'] as num?)?.toDouble();
        final markerLng = (location['lng'] as num?)?.toDouble();
        if (markerLat == null || markerLng == null) continue;

        final issueType = campaign['issue_type'] as String? ?? 'other';
        final hue = _issueTypeHues[issueType] ?? BitmapDescriptor.hueViolet;
        final campaignId = campaign['campaign_id'] as String? ?? '';

        markers.add(Marker(
          markerId: MarkerId(campaignId),
          position: LatLng(markerLat, markerLng),
          icon: BitmapDescriptor.defaultMarkerWithHue(hue),
          onTap: () => _showCampaignBottomSheet(campaign),
        ));
      }

      setState(() {
        _campaigns = campaignList;
        _markers = markers;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _isLoading = false;
        _errorMessage = e is ApiException
            ? e.message
            : 'Failed to load nearby issues.';
      });
    }
  }

  void _showCampaignBottomSheet(Map<String, dynamic> campaign) {
    setState(() => _selectedCampaign = campaign);
    showModalBottomSheet(
      context: context,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (_) => Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              campaign['title'] as String? ?? 'Untitled Issue',
              style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              children: [
                Chip(
                  label: Text(campaign['issue_type'] as String? ?? ''),
                  backgroundColor: Colors.blue[50],
                ),
                Chip(
                  label: Text('Severity ${campaign['severity']}'),
                  backgroundColor: Colors.orange[50],
                ),
                Chip(
                  label: Text('${campaign['citizen_count']} citizens'),
                  backgroundColor: Colors.green[50],
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              campaign['address'] as String? ?? '',
              style: const TextStyle(color: Colors.black54),
            ),
            const SizedBox(height: 8),
            Text(
              'Status: ${campaign['status'] ?? ''}',
              style: const TextStyle(fontWeight: FontWeight.w500),
            ),
            const SizedBox(height: 16),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: () {
                  Navigator.pop(context);
                  Navigator.push(
                    context,
                    MaterialPageRoute(
                      builder: (_) => CampaignDetailScreen(
                        campaignId: campaign['campaign_id'] as String? ?? '',
                      ),
                    ),
                  );
                },
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF1565C0),
                  foregroundColor: Colors.white,
                ),
                child: const Text('View Details'),
              ),
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('WardWatch'),
        backgroundColor: const Color(0xFF1565C0),
        foregroundColor: Colors.white,
        actions: [
          if (_isLoading)
            const Padding(
              padding: EdgeInsets.all(16),
              child: SizedBox(
                width: 20,
                height: 20,
                child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2),
              ),
            ),
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () {
              if (_userLocation != null) {
                _fetchNearbyCampaigns(_userLocation!.latitude, _userLocation!.longitude);
              } else {
                _initLocation();
              }
            },
          ),
        ],
      ),
      body: Stack(
        children: [
          _userLocation == null && !_isLoading
              ? Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Icon(Icons.location_off, size: 64, color: Colors.grey),
                      const SizedBox(height: 16),
                      Text(
                        _errorMessage.isNotEmpty
                            ? _errorMessage
                            : 'Fetching your location...',
                        textAlign: TextAlign.center,
                        style: const TextStyle(color: Colors.black54),
                      ),
                      const SizedBox(height: 16),
                      ElevatedButton(
                        onPressed: _initLocation,
                        child: const Text('Try Again'),
                      ),
                    ],
                  ),
                )
              : GoogleMap(
                  initialCameraPosition: CameraPosition(
                    target: _userLocation != null
                        ? LatLng(_userLocation!.latitude, _userLocation!.longitude)
                        : const LatLng(19.0760, 72.8777), // Mumbai default
                    zoom: 14,
                  ),
                  myLocationEnabled: true,
                  myLocationButtonEnabled: true,
                  markers: _markers,
                  onMapCreated: (controller) => _mapController = controller,
                ),
          if (_errorMessage.isNotEmpty && !_isLoading)
            Positioned(
              top: 8,
              left: 8,
              right: 8,
              child: Card(
                color: Colors.orange[50],
                child: Padding(
                  padding: const EdgeInsets.all(8),
                  child: Text(
                    _errorMessage,
                    style: const TextStyle(fontSize: 13),
                    textAlign: TextAlign.center,
                  ),
                ),
              ),
            ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => Navigator.push(
          context,
          MaterialPageRoute(builder: (_) => const CameraScreen()),
        ),
        backgroundColor: const Color(0xFF1565C0),
        foregroundColor: Colors.white,
        icon: const Icon(Icons.add_a_photo),
        label: const Text('Report Issue'),
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _selectedNavIndex,
        onDestinationSelected: (index) {
          setState(() => _selectedNavIndex = index);
          switch (index) {
            case 1:
              Navigator.push(context,
                  MaterialPageRoute(builder: (_) => const LeaderboardScreen()));
              break;
            case 2:
              Navigator.push(context,
                  MaterialPageRoute(builder: (_) => const ProfileScreen()));
              break;
          }
        },
        destinations: const [
          NavigationDestination(icon: Icon(Icons.map), label: 'Map'),
          NavigationDestination(icon: Icon(Icons.leaderboard), label: 'Leaderboard'),
          NavigationDestination(icon: Icon(Icons.person), label: 'Profile'),
        ],
      ),
    );
  }

  @override
  void dispose() {
    _mapController?.dispose();
    super.dispose();
  }
}
