import React from 'react';

// Component for displaying a single statistic bar
const StatBar = ({ value, max, side }) => {
  const width = Math.round((value / max) * 100);
  return (
    <div className={`flex ${side === 'left' ? 'justify-end' : 'justify-start'}`}>
      <div className="relative w-full max-w-[150px] h-6 bg-gray-100 rounded">
        <div 
          className={`absolute top-0 h-full bg-blue-500 rounded ${
            side === 'left' ? 'right-0' : 'left-0'
          }`}
          style={{ width: `${width}%` }}
        >
          <span className={`absolute ${side === 'left' ? 'right-full mr-2' : 'left-full ml-2'} top-1/2 -translate-y-1/2 text-sm`}>
            {value}
          </span>
        </div>
      </div>
    </div>
  );
};

const MatchStats = ({ homeStats, awayStats, gameDetails }) => {
  if (!homeStats || !awayStats) return null;

  const statConfigs = [
    { key: 'possessionPercentage', label: 'Possession %' },
    { key: 'shotsTotal', label: 'Total Shots' },
    { key: 'shotsOnTarget', label: 'Shots on Target' },
    { key: 'shotsOffTarget', label: 'Shots off Target' },
    { key: 'shotsBlocked', label: 'Blocked Shots' },
    { key: 'shotsSaved', label: 'Saves' },
    { key: 'foulsCommitted', label: 'Fouls' },
    { key: 'cornersWon', label: 'Corners' },
    { key: 'touchesInBox', label: 'Touches in Box' },
    { key: 'aerialsWon', label: 'Aerials Won' }
  ];

  // Find maximum value for each stat type to scale bars
  const maxValues = {};
  statConfigs.forEach(({ key }) => {
    maxValues[key] = Math.max(homeStats[key] || 0, awayStats[key] || 0);
  });

  return (
    <div className="space-y-8">
      {/* Match Header */}
      <div className="text-center">
        <h2 className="text-2xl font-bold mb-2">
          {gameDetails.opposition} ({gameDetails.venue})
        </h2>
        <div className="text-xl mb-2">{gameDetails.score}</div>
        <div className="text-sm text-gray-600">
          {gameDetails.competition} - {gameDetails.game_date}
        </div>
      </div>

      {/* Match Details */}
      <div className="grid grid-cols-2 gap-4 text-sm">
        <div className="space-y-2">
          <div><span className="font-medium">Attendance:</span> {gameDetails.attendance}</div>
          <div><span className="font-medium">Referee:</span> {gameDetails.referee}</div>
          <div><span className="font-medium">Kickoff:</span> {gameDetails.ko_time}</div>
        </div>
        <div className="space-y-2">
          <div><span className="font-medium">Stadium:</span> {gameDetails.stadium}</div>
          <div><span className="font-medium">League Position:</span> {gameDetails.league_pos}</div>
          <div><span className="font-medium">League Points:</span> {gameDetails.league_pts}</div>
        </div>
      </div>

      {/* Statistics Section */}
      <div>
        <h3 className="text-xl font-bold mb-4 text-center">Match Statistics</h3>
        <div className="grid grid-cols-3 gap-4 mb-6">
          <div className="text-center font-bold">{homeStats.team_name}</div>
          <div className="text-center font-bold">Statistics</div>
          <div className="text-center font-bold">{awayStats.team_name}</div>
        </div>
        
        <div className="space-y-4">
          {statConfigs.map(({ key, label }) => (
            <div key={key} className="grid grid-cols-3 gap-4 items-center">
              <StatBar 
                value={homeStats[key]} 
                max={maxValues[key]} 
                side="left" 
              />
              <div className="text-center text-sm">{label}</div>
              <StatBar 
                value={awayStats[key]} 
                max={maxValues[key]} 
                side="right" 
              />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default MatchStats;