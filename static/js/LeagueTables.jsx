import React from 'react';

const LeagueTable = ({ tableData }) => {
  if (!tableData || tableData.length === 0) return null;

  return (
    <div className="mt-8">
      <h3 className="text-xl font-bold mb-4 text-center">League Table</h3>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-100">
              <th className="p-2 text-left">Pos</th>
              <th className="p-2 text-left">Team</th>
              <th className="p-2 text-center">P</th>
              <th className="p-2 text-center">W</th>
              <th className="p-2 text-center">D</th>
              <th className="p-2 text-center">L</th>
              <th className="p-2 text-center">GF</th>
              <th className="p-2 text-center">GA</th>
              <th className="p-2 text-center">GD</th>
              <th className="p-2 text-center">Pts</th>
            </tr>
          </thead>
          <tbody>
            {tableData.map((row, index) => (
              <tr key={index} className="border-b hover:bg-gray-50">
                <td className="p-2">{row.pos}</td>
                <td className="p-2 font-medium">{row.team_name}</td>
                <td className="p-2 text-center">{row.pld}</td>
                <td className="p-2 text-center">{row.w}</td>
                <td className="p-2 text-center">{row.d}</td>
                <td className="p-2 text-center">{row.l}</td>
                <td className="p-2 text-center">{row.gf}</td>
                <td className="p-2 text-center">{row.ga}</td>
                <td className="p-2 text-center">{row.gd}</td>
                <td className="p-2 text-center font-bold">{row.pts}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default LeagueTable;