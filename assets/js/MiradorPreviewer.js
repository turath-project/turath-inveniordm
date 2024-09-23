import React, { useEffect } from 'react';
import PropTypes from 'prop-types';
import Mirador from 'mirador';

const MiradorPreviewer = ({ file, record }) => {
  useEffect(() => {
    const manifestUrl = `/api/iiif/record/${record.id}/manifest`;

    Mirador.viewer({
      id: 'mirador-viewer',
      windows: [
        {
          manifestId: manifestUrl,
        },
      ],
    });
  }, [record.id]);

  return <div id="mirador-viewer"></div>;
};

MiradorPreviewer.propTypes = {
  file: PropTypes.object.isRequired,
  record: PropTypes.object.isRequired,
};

export default MiradorPreviewer;
