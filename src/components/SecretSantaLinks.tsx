import React from "react";
import { DownloadSimple, EnvelopeSimple } from "@phosphor-icons/react";
import { useTranslation } from "react-i18next";
import { CopyButton } from "./CopyButton";
import { buildEmailExport, generateAssignmentLink, generateCSV } from "../utils/links";
import { isValidEmail } from "../utils/email";
import { Participant } from "../types";
import { GeneratedPairs, generateGenerationHash } from "../utils/generatePairs";

interface SecretSantaLinksProps {
  assignments: GeneratedPairs;
  instructions?: string;
  participants: Record<string, Participant>;
  onGeneratePairs: () => void;
}

export function SecretSantaLinks({ assignments, instructions, participants, onGeneratePairs }: SecretSantaLinksProps) {
  const { t } = useTranslation();

  const currentHash = generateGenerationHash(participants);
  const hasChanged = currentHash !== assignments.hash;

  const adjustedPairings = assignments.pairings.map(({giver, receiver}): [string, string, string | undefined, string | undefined] => [
    participants[giver.id]?.name ?? giver.name,
    participants[receiver.id]?.name ?? receiver.name,
    participants[receiver.id]?.hint,
    participants[giver.id]?.email,
  ]);

  const missingEmailCount = adjustedPairings.filter(([, , , email]) => !isValidEmail(email)).length;

  adjustedPairings.sort((a, b) => {
    return a[0].localeCompare(b[0]);
  });

  const downloadFile = (content: string, type: string, filename: string) => {
    const blob = new Blob([content], { type });
    const url = window.URL.createObjectURL(blob);

    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();

    window.URL.revokeObjectURL(url);
  };

  const handleExportCSV = () => {
    const csvContent = generateCSV(adjustedPairings.map(([giver, receiver]) => [giver, receiver]));
    downloadFile(csvContent, 'text/csv', 'secret-santa-assignments.csv');
  };

  const handleExportEmails = async () => {
    const entries = await Promise.all(adjustedPairings.map(async ([giver, receiver, hint, email]) => ({
      giver,
      email,
      link: await generateAssignmentLink(giver, receiver, hint, instructions),
    })));

    const exportData = buildEmailExport(entries);
    downloadFile(JSON.stringify(exportData, null, 2), 'application/json', 'secret-santa-emails.json');
  };

  return <>
    {hasChanged && (
      <div className="mb-2 p-3 bg-yellow-100 border border-yellow-400 text-yellow-800 rounded">
        <p className="text-sm">
          {t('links.warningParticipantsChanged')}
        </p>
        <button
          className="mt-2 w-full px-2 py-1 bg-yellow-700/40 rounded hover:bg-yellow-700/50 text-center text-white text-xs"
          onClick={onGeneratePairs}
        >
          {t('links.resetAssignments')}
        </button>
      </div>
    )}
    <div className="p-4 bg-gray-50 rounded-lg">
      <div className="flex space-x-4 items-center mb-4">
        <p className="text-gray-600 text-balance">
          {t('links.shareInstructions')}
        </p>
        <button
          onClick={handleExportCSV}
          className="p-2 bg-green-500 text-white rounded hover:bg-green-600 flex flex-none items-center gap-2"
        >
          <DownloadSimple size={20} weight="bold" />
          {t('links.exportCSV')}
        </button>
      </div>
      <div className="mb-4 p-3 bg-white border rounded">
        <button
          onClick={handleExportEmails}
          disabled={hasChanged}
          title={missingEmailCount > 0 ? t('links.missingEmails', { count: missingEmailCount }) : undefined}
          className="w-full p-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
        >
          <EnvelopeSimple size={20} weight="bold" />
          {t('links.exportEmailFile')}
        </button>
        {missingEmailCount > 0 && (
          <p className="mt-2 text-xs text-yellow-700">
            {t('links.missingEmails', { count: missingEmailCount })}
          </p>
        )}
        <p className="mt-2 text-xs text-gray-500">
          {t('links.exportEmailFileWarning')}
        </p>
      </div>
      <div className="grid grid-cols-[minmax(100px,auto)_1fr] gap-3">
        {adjustedPairings.map(([giver, receiver, hint]) => (
          <React.Fragment key={giver}>
            <span className="font-medium self-center">
              {giver}:
            </span>
            <CopyButton
              textToCopy={() => generateAssignmentLink(giver, receiver, hint, instructions)}
              className="p-2 bg-blue-500 text-white rounded hover:bg-blue-600 flex items-center justify-center gap-2"
            >
              {t('links.copySecretLink')}
            </CopyButton>
          </React.Fragment>
        ))}
      </div>
    </div>
  </>;
}