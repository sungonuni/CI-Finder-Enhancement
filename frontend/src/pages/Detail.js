import './App.css';
import React, { useState, useRef } from 'react';
import { useNavigate, useParams, useLocation } from 'react-router-dom';

import { Space } from 'antd';
import { Layout, Menu, theme, message} from 'antd';
import { Card, Col } from 'antd';
import { Tabs } from 'antd';
import { Descriptions } from 'antd';
import { SearchOutlined, DownloadOutlined, LinkOutlined } from '@ant-design/icons';
import { Button, Input, Table } from 'antd';
import Highlighter from 'react-highlight-words';

import axios from 'axios';

const PROXY = window.location.hostname === 'localhost' ? '/api' : '';
const DOWNLOADURL = `${PROXY}/Download`;

const { Header, Content, Footer } = Layout;

/**
 * Make JIRA link via ticket number in B2B name
 * @param {string} B2Bname 
 * @returns {string}
 */
function MakeJIRALink(B2Bname) {
  let B2BJiraNum = B2Bname.match(/((?<=[a-zA-z-]{2,3})|)[0-9]{5}/g);
  if (B2BJiraNum !== null) {
    return ('https://frkengjira01.spirentcom.com/browse/LS-'+B2BJiraNum[0])
  }
  return ''
} 

/**
 * Make variable list for Coexisted List (Tcl Variables which exist in STE and B2B)
 * @param {Array} TestCaseList list of B2B's test case
 * @param {string} category match or mismatch 
 * @returns 
 */
function CreateCoexistedList(TestCaseList, category) {
  let TableData = [];
  let idx = 0;
  for (let TC of Object.keys(TestCaseList)) {
    if (TestCaseList[TC].boolean[category] !== undefined) { // If Test Case doesn't have any string, boolean variable: ignore it
      for (let DataType of Object.keys(TestCaseList[TC])) {
        if (Object.keys(TestCaseList[TC][DataType]).length === 0) { // If Test Case has string, boolean key but no value: ignore it
          continue;
        }
        for (let TCL of Object.keys(TestCaseList[TC][DataType][category])) {
          let row = {};
          row['key'] = idx;
          row['testCase'] = TC;
          row['name'] = TCL;
          row['dataType'] = DataType
          row['ste'] = (category === 'match' ? 
            TestCaseList[TC][DataType][category][TCL].toString() : 
            TestCaseList[TC][DataType][category][TCL].input.toString());
          row['b2b'] = (category === 'match' ? 
            TestCaseList[TC][DataType][category][TCL].toString() : 
            TestCaseList[TC][DataType][category][TCL].target.toString());
          TableData.push(row);
          idx += 1;
        }
      }
    }
  }
  return TableData;
}

/**
 * Make variable list for non-coexisted List (Tcl Variables which exist in STE and B2B)
 * @param {*} TestCaseList list of B2B's test case
 * @param {*} category match or mismatch 
 * @returns 
 */
function CreateNoCoexistedList(TestCaseList, category) { // testData.info[id].testCase, onlyinput or onlyCI
  let TableData = [];
  let idx = 0;
  for (let TC of Object.keys(TestCaseList)) {
    if (TestCaseList[TC].boolean[category] !== undefined) {
      for (let DataType of Object.keys(TestCaseList[TC])){
        if (Object.keys(TestCaseList[TC].string).length === 0) {
          continue;
        } 
        for (let TCL of Object.keys(TestCaseList[TC][DataType][category])) {
          let row = {};
          row['key'] = idx;
          row['testCase'] = TC;
          row['name'] = TCL;
          row['dataType'] = DataType
          row['value'] = TestCaseList[TC][DataType][category][TCL].toString();
          TableData.push(row);
          idx += 1;
        }
      }
    }
  }
  return TableData;
}


// Detail page
function ShowDetails() {
  const navigate = useNavigate();
  const { id } = useParams();
  const { state } = useLocation();

  const [searchText, setSearchText] = useState('');
  const [searchedColumn, setSearchedColumn] = useState('');
  const searchInput = useRef(null);

  const testData = state.B2BListParams;
  const inputInfo = state.inputInfoParams;

  const onClickLogo = (event) => {
    navigate(-3);
  };

  // const menuItem = [ // Title menu
  //   {label: 'Dashboard', icon: React.createElement(PlayCircleOutlined)}, 
  //   {label: 'Result', icon: React.createElement(LaptopOutlined)}
  // ];

  const bodyStyle = {
    maxHeight: '100%',
  };

  const {
    token: { colorBgContainer },
  } = theme.useToken();


  // infos
  /**
   * Show the input STE’s information and B2B's information.
   */
  const showInfo = (kind) => {
    let input = {};
    let tcNameList = [];
    let isB2B = Boolean();
    let isJIRA = Boolean();
    let isDownload = Boolean();

    if (kind === "input") {
      input = inputInfo;
      tcNameList = Object.keys(input.tclData).map((tcName) => tcName+' ('+input.tclData[tcName].string.TestActivity+')');
    } else if (kind === "B2B") {
      input = testData.info[id];
      for (let tcName of Object.keys(input.tclData)) {
        try {
          tcNameList.push(tcName + ' (' + input.testCase[tcName].string.TestActivity.target + ')');
        } catch {
          tcNameList.push(tcName + ' (undefined)');
        }
      }

      isB2B = true;
      isJIRA = (MakeJIRALink(input.name).length !== 0 ? true : false);
      isDownload = (input.status === "1" ? true : false);
    } else {}


    tcNameList.sort();

    return (
      <>
        <Descriptions.Item label="Name" span={2}>
          {input.name}
        </Descriptions.Item>
        <Descriptions.Item label="Number of test case">
          {tcNameList.length}
        </Descriptions.Item>
        <Descriptions.Item label="Test case list" span={2}>
          {tcNameList.map((name, _) => (
            <Col key={name}>
              {name}
            </Col>
          ))}
        </Descriptions.Item>
        {isB2B && (
          <>
            <Descriptions.Item label="Score">
              {input.score}
            </Descriptions.Item>
            <Descriptions.Item label="Action">
              <Space>
                {isDownload && ( // If this B2B cannot be download, the button is disappeared.
                  <Button
                    type="primary"
                    onClick={onClickDownload}
                    icon={<DownloadOutlined />}
                  >
                    Download from CIphase2
                  </Button>
                )}
                {isJIRA && ( // If this B2B name doesn't contain the JIRA ticket number, the button is disappeared.
                  <Button
                  type="default"
                  onClick={onClickJIRA}
                  icon={<LinkOutlined />}
                  >
                  Move to JIRA ticket
                  </Button>
                )}
              </Space>
            </Descriptions.Item>
          </>
        )}
      </>
    );
  };

  /**
   * Call /Download API to the server with query parameter
   * - Parameter
   *  name: The name of B2B
   *  address: TAS address
   *  libraryId: TAS Library ID
   *  deleteSte: STE delete config
   * @param {*} e 
   * @param {string} B2B 
   */
  const onClickDownload = async(e) => {
    const hideMessage = message.loading(`Try to download the B2B`, 0);
    try{
      const res = await axios.post(DOWNLOADURL, null, {
        params: {
          name: testData.info[id].name,
          address : testData.info[id].TAS.address,
          libraryId: testData.info[id].TAS.libraryId,
          deleteSte: true
        },
        headers: {
          'Content-Type': 'application/json'
        },
        responseType: 'blob'
      }); 

      message.success(`Success to download!`);

      let url  = window.URL.createObjectURL(res.data);
      let a = document.createElement('a');
      a.href = url;
      a.download = testData.info[id].name+'.ste';
      document.body.appendChild(a);
      a.click();
      a.remove();
    }
    catch(e) {
      message.error(`cannot download ste file`);
    }
    finally {
      hideMessage();
    }
  };

  /**
   * Forward the user to JIRA ticket link.
   * @param {*} e 
   */
  const onClickJIRA = async(e) => {
    window.open(MakeJIRALink(testData.info[id].name));
  }

  // Tables
  const handleSearch = (selectedKeys, confirm, dataIndex) => {
    confirm();
    setSearchText(selectedKeys[0]);
    setSearchedColumn(dataIndex);
  };

  const handleReset = (clearFilters) => {
    clearFilters();
    setSearchText('');
  };

  /**
   * Functional componants for variable name search in Analysis table
   * @param {Array} dataIndex 
   * @returns 
   */
  const getColumnSearchProps = (dataIndex) => ({
    filterDropdown: ({ setSelectedKeys, selectedKeys, confirm, clearFilters, close }) => (
      <div
        style={{
          padding: 8,
        }}
        onKeyDown={(e) => e.stopPropagation()}
      >
        <Input
          ref={searchInput}
          placeholder={`Search ${dataIndex}`}
          value={selectedKeys[0]}
          onChange={(e) => setSelectedKeys(e.target.value ? [e.target.value] : [])}
          onPressEnter={() => handleSearch(selectedKeys, confirm, dataIndex)}
          style={{
            marginBottom: 8,
            display: 'block',
          }}
        />
        <Space>
          <Button
            type="primary"
            onClick={() => handleSearch(selectedKeys, confirm, dataIndex)}
            icon={<SearchOutlined />}
            size="small"
            style={{
              width: 90,
            }}
          >
            Search
          </Button>
          <Button
            onClick={() => clearFilters && handleReset(clearFilters)}
            size="small"
            style={{
              width: 90,
            }}
          >
            Reset
          </Button>
          <Button
            type="link"
            size="small"
            onClick={() => {
              confirm({
                closeDropdown: false,
              });
              setSearchText(selectedKeys[0]);
              setSearchedColumn(dataIndex);
            }}
          >
            Filter
          </Button>
          <Button
            type="link"
            size="small"
            onClick={() => {
              close();
            }}
          >
            close
          </Button>
        </Space>
      </div>
    ),
    filterIcon: (filtered) => (
      <SearchOutlined
        style={{
          color: filtered ? '#1890ff' : undefined,
        }}
      />
    ),
    onFilter: (value, record) =>
      record[dataIndex].toString().toLowerCase().includes(value.toLowerCase()),
    onFilterDropdownOpenChange: (visible) => {
      if (visible) {
        setTimeout(() => searchInput.current?.select(), 100);
      }
    },
    render: (text) =>
      searchedColumn === dataIndex ? (
        <Highlighter
          highlightStyle={{
            backgroundColor: '#ffc069',
            padding: 0,
          }}
          searchWords={[searchText]}
          autoEscape
          textToHighlight={text ? text.toString() : ''}
        />
      ) : (
        text
      ),
  });

  const bothExistTClColumns = [
    {
      title: 'Test Case',
      dataIndex: 'testCase',
      filters: 
        Object.keys(inputInfo.tclData).map((TC, _) => ({
          text: TC,
          value: TC,
        })),
      defaultSortOrder: 'ascend',
      sorter: (a, b) => a.testCase.localeCompare(b.testCase),
      onFilter: (value, record) => record.testCase === value,
    },
    {
      title: 'Name',
      dataIndex: 'name',
      defaultSortOrder: 'ascend',
      ...getColumnSearchProps('name'),
      sorter: (a, b) => a.name.localeCompare(b.name),
    },
    {
      title: 'Data Type',
      dataIndex: 'dataType',
      filters: [
        {
          text: "boolean",
          value: "boolean",
        },
        {
          text: "string",
          value: "string",
        },
      ],
      onFilter: (value, record) => record.dataType === value,
    },
    {
      title: 'STE',
      dataIndex: 'ste',
      filters: [
        {
          text: "true",
          value: "true",
        },
        {
          text: "false",
          value: "false",
        },
      ],
      onFilter: (value, record) => record.ste === value,
    },
    {
      title: 'B2B',
      dataIndex: 'b2b',
      filters: [
        {
          text: "true",
          value: "true",
        },
        {
          text: "false",
          value: "false",
        },
      ],
      onFilter: (value, record) => record.b2b === value,
    },
  ];

  const noExistTClColumns = [
    {
      title: 'Test Case',
      dataIndex: 'testCase',
      filters: 
        Object.keys(inputInfo.tclData).map((TC, _) => ({
          text: TC,
          value: TC,
        })),
      onFilter: (value, record) => record.testCase === value,
    },
    {
      title: 'Name',
      dataIndex: 'name',
      defaultSortOrder: 'ascend',
      ...getColumnSearchProps('name'),
      sorter: (a, b) => a.name.localeCompare(b.name),
    },
    {
      title: 'Data Type',
      dataIndex: 'dataType',
      filters: [
        {
          text: "boolean",
          value: "boolean",
        },
        {
          text: "string",
          value: "string",
        },
      ],
      onFilter: (value, record) => record.dataType === value,
    },
    {
      title: 'Value',
      dataIndex: 'value',
      filters: [
        {
          text: "true",
          value: "true",
        },
        {
          text: "false",
          value: "false",
        },
      ],
      onFilter: (value, record) => record.value === value,
    },
  ];

  const matchedTableData = CreateCoexistedList(testData.info[id].testCase, 'match');
  const notMatchedTableData = CreateCoexistedList(testData.info[id].testCase, 'mismatch');
  const onlySteTableData = CreateNoCoexistedList(testData.info[id].testCase, 'onlyinput');
  const onlyB2BTableData = CreateNoCoexistedList(testData.info[id].testCase, 'onlyCI');
  
  const resultTabs = [
    {
      key: '1',
      label: `Matched`,
      children: (
        <Table 
          columns={bothExistTClColumns} 
          dataSource={matchedTableData} 
          style={{
            width: '100%',
            height: 500,
          }}
        />
      ),
    },
    {
      key: '2',
      label: `Not matched`,
      children: (
        <Table
          columns={bothExistTClColumns}
          dataSource={notMatchedTableData}
          style={{
            width: '100%',
            height: 500,
          }}
        />
      ),
    },
    {
      key: '3',
      label: `Only in STE`,
      children: (
        <Table 
          columns={noExistTClColumns}
          dataSource={onlySteTableData}
          style={{
            width: '100%',
            height: 500,
          }}
        />
      ),
    },
    {
      key: '4',
      label: `Only in CI B2B`,
      children: (
        <Table 
          columns={noExistTClColumns}
          dataSource={onlyB2BTableData}
          style={{
            width: '100%',
            height: 500,
          }}
        />
      ),
    },
  ];

  return (
    <>
      <Layout className="layout">
        <Header
          style={{ backgroundColor: "#2185D0" }}
        >
          <div className="logo" onClick={onClickLogo}/>
          <Menu
            style={{ backgroundColor: "#2185D0", color: "#D0D0D0" }}
            mode="horizontal"
            defaultSelectedKeys={['1']}
          />
        </Header>
        <Layout style={{ minHeight: '80vh' }}>
          <Content style={{ padding: '1% 3%' }}>
            <div className="site-card-wrapper" style={{ padding: '2% 5%' }}>
              <>
                <Space direction="vertical" size="middle" style={{ display: 'flex' }}>
                  <Card
                    title="Information"
                    style={{
                      width: '100%',
                      height: 580,
                      maxHeight: 580,
                      padding: '1% 3%',
                      overflow: "auto"
                    }}
                    bodyStyle={bodyStyle}
                  >
                    <Space direction="vertical" size="middle" style={{ display: 'flex' }}>
                      <Descriptions title="Input test suite" bordered>
                        {showInfo("input")}
                      </Descriptions>
                      <Descriptions title="CI B2B test suite" bordered>
                        {showInfo("B2B")}
                      </Descriptions>
                    </Space>
                  </Card>
                  <Card
                    title="Analysis"
                    style={{
                      width: '100%',
                      height: 900,
                      maxHeight: 900,
                      padding: '1% 3%',
                      overflow: "auto"
                    }}
                    bodyStyle={bodyStyle}
                  >
                    <Tabs 
                      defaultActiveKey="1" 
                      items={resultTabs}
                      style={{
                        width: '100%',
                      }}
                    />
                  </Card>
                </Space>
              </>
            </div>
          </Content>
        </Layout>
        <Footer style={{ textAlign: 'center' }}>©2023 Spirent Communications, Inc. All rights reserved.</Footer>
      </Layout>
    </>
  );
}

export default ShowDetails;