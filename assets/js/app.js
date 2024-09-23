import React from 'react';
import ReactDOM from 'react-dom';
import { FilePreviewer } from 'invenio-previewer';
import miradorPreviewers from 'invenio-previewer-mirador/assets/js/previewer_config';

const file = window.previewerFile;
const record = window.previewerRecord;

ReactDOM.render(
  <FilePreviewer file={file} record={record} previewers={miradorPreviewers} />,
  document.getElementById('app')
);
